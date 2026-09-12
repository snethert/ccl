"""Independent input witnesses for a projection. Success is NOT census acceptance."""
from collections import defaultdict
from exchange import ident, fixed_point
from effects import module


class Rejected(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(code + ': ' + detail)


def require(value, code, detail):
    if not value:
        raise Rejected(code, detail)


def witnesses(rebuild_events, cold_events):
    # Deliberately read the raw streams here, rather than trusting the effect
    # producer's row counts, summaries, or lists of supposedly required edges.
    import json
    result = {k: {} for k in ('compile', 'load', 'startup', 'returns')}
    for path, kinds in [(rebuild_events, {'compile-initializer-enter': 'compile',
                                         'load-initializer-emitted': 'load'}),
                        (cold_events, {'startup-enter': 'startup'})]:
        active = []
        for line in path.open():
            e = json.loads(line)
            if e['kind'] in kinds:
                result[kinds[e['kind']]][e['sequence']] = e
            if e['kind'] in ('compile-initializer-enter', 'startup-enter'):
                e['expected_compiled_during'] = []
                active.append(e)
            if e['kind'] == 'before-pass2' and active:
                active[-1]['expected_compiled_during'].append(e['payload']['function_id'])
            if e['kind'] in ('compile-initializer-return', 'startup-return'):
                result['returns'][path.name, e['sequence']] = e
                require(bool(active), 'RAW_EFFECT_PAIR', str(e['sequence']))
                entry = active.pop()
                require(entry['source'] == e['source'] and entry['source_position'] == e['source_position'],
                        'RAW_EFFECT_PAIR', str(e['sequence']))
                entry['expected_return'] = e['sequence']
        require(not active, 'RAW_EFFECT_PAIR', 'missing return')
    return result


def check(graph, joins, image, observed, candidates, seeds, raw, lowering, stub):
    nodes = {n['id']: n for n in graph['nodes']}
    require(len(nodes) == len(graph['nodes']), 'DUPLICATE_NODE', 'node identities must be unique')
    for prefix, rows in [('native', image['functions']), ('compiled', observed['nodes']),
                         ('operator', image['operators'])]:
        expected = {ident(prefix, r['id']) for r in rows}
        actual = {i for i in nodes if i.startswith(prefix + ':')}
        require(expected == actual, 'NODE_COVERAGE', prefix)
    require(all(n['required'] for n in nodes.values()), 'REQUIRED_FLAG', 'a retained dependency was made optional')
    edges = defaultdict(list)
    for e in graph['edges']:
        require(e['from'] in nodes and set(e['targets']) <= nodes.keys(), 'EDGE_REFERENCE', e['evidence'])
        edges[e['from'], e['evidence']].append(e)

    def one(source, evidence, targets, resolution='complete', phase=None, origin=None):
        rows = edges[source, evidence]
        require(len(rows) == 1, 'EDGE_COVERAGE', evidence)
        e = rows[0]
        require(set(e['targets']) == set(targets) and len(set(e['targets'])) == len(e['targets']),
                'EDGE_TARGETS', evidence)
        require(e['resolution'] == resolution, 'UNPROVED_PROMOTION', evidence)
        if phase is not None:
            require(e['phase'] == phase, 'EDGE_PHASE', evidence)
        if origin is not None:
            require(e['origin'] == origin, 'EDGE_ORIGIN', evidence)

    expected_seeds = [ident('native', s['native_function']) for s in candidates['seeds']]
    require(graph['seeds'] == expected_seeds, 'SEED_COVERAGE', 'review proposal differs')
    # Independent named entrypoint witnesses: removing LOAD from both manifests
    # must not make the narrowed seed set pass this observer-specific check.
    for name in ['COMMON-LISP::LOAD', 'CCL::%FASLOAD', 'CCL::RESTORE-LISP-POINTERS',
                 'COMMON-LISP::READ', 'COMMON-LISP::ERROR']:
        bindings = [b for b in image['bindings'] if b['namespace'] == 'function' and b['name'] == name]
        require(len(bindings) == 1 and ident('native', bindings[0]['function']) in graph['seeds'],
                'LOADER_SEED', name)
    require(graph['seed_review'] == seeds['review_disposition'] == 'PROPOSED_REQUIRES_INDEPENDENT_REVIEW',
            'REVIEW_PROMOTION', 'this producer cannot approve the seed set')

    for op in image['operators']:
        if op['function'] is not None:
            one(ident('operator', op['id']), 'image/operator-handler/' + str(op['id']),
                [ident('handler', op['id'])], phase='compile', origin='observed')
            one(ident('handler', op['id']), 'image/handler-code/' + str(op['id']),
                [ident('native', op['function'])], phase='compile', origin='observed')
            one(ident('handler', op['id']), 'lowering/whole-native-template-candidates/' + str(op['id']),
                [ident('vinsn', v['name']) for v in image['vinsns']], 'unresolved', 'compile', 'conservative')
    require({i for i in nodes if i.startswith('vinsn:')} == {ident('vinsn', v['name']) for v in image['vinsns']},
            'LOWERING_COVERAGE', 'evaluated template omitted')
    require(joins['lowering'] == lowering, 'LOWERING_COVERAGE', 'decoded metadata changed')
    for v in lowering:
        for op in v['opcodes']:
            one(ident('vinsn', v['name']), 'lowering/opcode/' + v['name'] + '/' + str(op[0]),
                [ident('lap', op[0])], phase='compile', origin='observed')

    for f in image['functions']:
        if f['literal_functions']:
            one(ident('native', f['id']), 'image/literals/' + str(f['id']),
                [ident('native', t) for t in f['literal_functions']], phase='run', origin='observed')
    for f in observed['nodes']:
        if f['operators']:
            one(ident('compiled', f['id']), 'r7/operators/' + str(f['id']),
                [ident('operator', t) for t in f['operators']], phase='compile', origin='observed')
    def walk_stub(f):
        yield f
        for child in f['inner_functions']:
            yield from walk_stub(child)
    stub_functions = [f for row in stub['rows'] for f in walk_stub(row['function'])]
    require({i for i in nodes if i.startswith('stub:')} == {ident('stub', f['function_id']) for f in stub_functions},
            'STUB_COVERAGE', 'registered front-end identities omitted')
    known_bindings = {b['name'] for b in candidates['global_bindings']}
    for f in stub_functions:
        one(ident('stub', f['function_id']), 'stub/operator-slots/' + str(f['function_id']),
            [ident('operator', op['id']) for op in f['operators']], phase='compile', origin='observed')
        for kind in ('calls', 'function_references'):
            for index, call in enumerate(f[kind]):
                targets = [ident('stub', t['id']) if t['kind'] == 'function' else
                           ident('binding' if t['name'] in known_bindings else 'stub-binding', t['name'])
                           for t in call['dependency']['targets']]
                evidence = f'stub/{kind}/{f["function_id"]}/{index}'
                if targets:
                    one(ident('stub', f['function_id']), evidence, targets, phase='run', origin='observed')
                else:
                    rows = edges[ident('stub', f['function_id']), evidence]
                    require(len(rows) == 1 and rows[0]['resolution'] == 'unresolved', 'STUB_UNKNOWN', evidence)
    # Every original site has its own witness, including unresolved sites.
    # Check the finite candidate union itself, not just its size or a label.
    universe = {ident('native', f['id']) for f in image['functions']}
    universe.update(ident('compiled', f['id']) for f in observed['nodes'])
    member_sets = defaultdict(set)
    for e in graph['edges']:
        if e['evidence'].startswith('members/'):
            member_sets[e['from']].update(e['targets'])
    covered_cache = {}
    for kind in ('calls', 'function_references'):
        for index, call in enumerate(observed[kind]):
            source, evidence = ident('compiled', call['caller']), f'r7/{kind}/{index}'
            targets = call['dependency']['targets']
            if targets:
                expected = [ident('compiled', t['id']) if t['kind'] == 'function' else ident('binding', t['name'])
                            for t in targets]
                one(source, evidence, expected, phase='run', origin='observed')
            else:
                rows = edges[source, evidence]
                require(len(rows) == 1 and rows[0]['resolution'] == 'unresolved',
                        'UNKNOWN_CALL', evidence)
                e = rows[0]
                surface = tuple(e['targets'])
                if surface not in covered_cache:
                    covered_cache[surface] = (set().union(*(member_sets[t] for t in surface)) & universe) == universe
                require(covered_cache[surface], 'CANDIDATE_OMISSION', evidence)
                require(e['phase'] == 'run' and e['origin'] == 'conservative', 'UNKNOWN_CALL', evidence)
    for b in candidates['global_bindings']:
        key, evidence = ident('binding', b['name']), 'candidates/targets/' + b['name']
        expected = {ident('compiled', t) for t in b['compiler_functions']}
        expected.update(ident('native', t['function']) for t in b['native_bindings'])
        rows = edges[key, evidence]
        require(len(rows) == 1 and rows[0]['resolution'] == 'unresolved', 'BINDING_COVERAGE', b['name'])
        if expected:
            require(set(rows[0]['targets']) == expected, 'BINDING_COVERAGE', b['name'])

    init = {i['node']: i for i in graph['initializers']}
    require(len(init) == len(graph['initializers']), 'INITIALIZER_COVERAGE', 'duplicate initializer')
    for kind, prefix, field in [('compile', 'init-compile', 'enter'), ('load', 'init-load', 'sequence'),
                                 ('startup', 'init-startup', 'enter')]:
        expected = {ident(prefix, seq) for seq in raw[kind]}
        actual = {i for i in init if i.startswith(prefix + ':')}
        require(actual == expected, 'INITIALIZER_COVERAGE', kind)
        rows = joins['effects'][kind]
        require({r[field] for r in rows} == set(raw[kind]) and len(rows) == len(raw[kind]),
                'EFFECT_WITNESS', kind)
        for row in rows:
            event = raw[kind][row[field]]
            require(row['preview' if kind != 'startup' else 'name'] == event['payload'], 'EFFECT_WITNESS', str(row[field]))
            if kind != 'startup':
                require(row['module'] == module(event['source']) and row['source_position'] == event['source_position'],
                        'EFFECT_WITNESS', 'source location ' + str(row[field]))
            if kind in ('compile', 'startup'):
                log = 'observed-rebuild.jsonl' if kind == 'compile' else 'observed-cold-start.jsonl'
                returned = raw['returns'].get((log, row['return']))
                require(returned is not None and row['return'] == event['expected_return'] and
                        returned['payload'] == row['return_preview' if kind == 'compile' else 'name'],
                        'EFFECT_RETURN', str(row[field]))
            key = ident(prefix, row[field])
            if kind in ('compile', 'load'):
                require(nodes[key]['disposition'] == 'unresolved' and init[key]['prerequisites'] == [] and
                        init[key]['rank'] == 0 and ('NOT_PROVED' if kind == 'compile' else 'NOT_OBSERVED') in init[key]['completion_assertion'],
                        'INITIALIZER_PROMOTION', key)
            if kind == 'compile' and row['compiled_during']:
                one(key, 'effects/compiled-during/' + str(row['enter']),
                    [ident('compiled', f) for f in row['compiled_during']], phase='compile', origin='observed')
            if kind == 'compile':
                require(row['compiled_during'] == event['expected_compiled_during'], 'EFFECT_BODY_OMISSION', key)
    pre_names = ['CCL::%REVIVE-SYSTEM-LOCKS', 'CCL::REFRESH-EXTERNAL-ENTRYPOINTS',
                 'CCL::RESTORE-PASCAL-FUNCTIONS', 'CCL::INITIALIZE-INTERACTIVE-STREAMS']
    schedule = [ident('init-pre', name) for name in pre_names]
    schedule += [ident('init-startup', seq) for seq in sorted(raw['startup'])]
    for rank, key in enumerate(schedule, 1):
        expected = [] if rank == 1 else [schedule[rank - 2]]
        require(key in init and init[key]['prerequisites'] == expected and init[key]['rank'] == rank,
                'STARTUP_PREREQUISITE', key)
    first_callback = min(raw['startup'])
    for name in pre_names:
        key = ident('init-pre', name)
        require(nodes[key]['disposition'] == 'implemented' and
                init[key]['completion_assertion'] == 'INFERRED_FROM_SOURCE: first callback entry at cold event ' +
                str(first_callback) + ' requires this preceding call to have returned normally.',
                'STARTUP_COMPLETION', key)
    callbacks = [fn for group in image['startup_groups'] for fn in group['functions']]
    for row, fn in zip(joins['effects']['startup'], callbacks):
        require(row['function'] == fn['function'] and row['name'] == fn['name'], 'CALLBACK_IDENTITY', row['name'])
        one(ident('init-startup', row['enter']), 'startup/code/' + str(row['enter']),
            [ident('native', fn['function'])], phase='callback', origin='observed')
    for name in ['candidate-bound', 'seed-review', 'subprimitive-callers', 'imports', 'stores',
                 'wasm-dispositions', 'target-source-coverage', 'macroexpand-dependencies']:
        key = ident('gap', name)
        require(key in nodes and nodes[key]['disposition'] == 'unresolved' and nodes[key]['implementation'] is None,
                'GAP_CONCEALED', name)

    expected_members = defaultdict(set)
    for f in image['functions']:
        key = ident('native', f['id'])
        expected_members['@clean-image'].add(key)
        if f['source']:
            expected_members[module(f['source'])].add(key)
    for f in observed['nodes']:
        for source in f['sources']:
            expected_members[module(source)].add(ident('compiled', f['id']))
    for kind, prefix in [('compile', 'init-compile'), ('load', 'init-load')]:
        for seq, event in raw[kind].items():
            expected_members[module(event['source'])].add(ident(prefix, seq))
    expected_members['@census-stub-corpus'].update(ident('stub', f['function_id']) for f in stub_functions)
    for source, members in expected_members.items():
        key = ident('module', source)
        one(key, 'members/' + source, members)
        for child in members:
            one(child, 'provenance/' + source + '/' + child, [key])

    reachable = fixed_point(graph)
    require(reachable == set(nodes), 'CLOSURE_COVERAGE', 'required inventory outside conservative projection')
    require(graph['observed_modules'] == [ident('module', '@r5-traced-image')], 'TRACE_MODULES', 'trace opens r5 image, not r7 or source files')
    require({r['node'] for r in graph['unobserved_modules']} ==
            {i for i in reachable if nodes[i]['kind'] == 'module'} - set(graph['observed_modules']),
            'TRACE_MODULES', 'unobserved module omitted')
    return {'status': 'PASS', 'scope': 'Projection coverage against retained inputs only; LL15 qualification remains BLOCKED.'}
