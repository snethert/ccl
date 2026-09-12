"""Project retained observations into census v1, keeping unproved joins unresolved."""
from collections import defaultdict, Counter, deque
from urllib.parse import quote
from effects import module

BASELINE = 'c994217adc56b3f8a564526cee4695893ac84d86'
TESTS = ['S0-LL15-b', 'S0-LL15-c']


def ident(kind, value):
    return kind + ':' + quote(str(value), safe='/@.-_')


def fixed_point(graph):
    outgoing = defaultdict(set)
    for edge in graph['edges']:
        outgoing[edge['from']].update(edge['targets'])
    reachable = set(graph['seeds'])
    queue = deque(sorted(reachable))
    while queue:
        for target in outgoing[queue.popleft()] - reachable:
            reachable.add(target)
            queue.append(target)
    return reachable


def build(image, observed, candidates, seeds, effects, lowering, stub, identities):
    nodes, edges, initializers = {}, [], []
    def node(key, kind, evidence, implementation=None, reason='', unresolved=False):
        if key in nodes:
            raise ValueError('duplicate census node: ' + key)
        nodes[key] = {'id': key, 'kind': kind, 'disposition': 'unresolved' if unresolved else 'implemented',
                      'required': True, 'implementation': implementation, 'evidence': evidence,
                      'tests': TESTS, 'reason': reason}
        return key
    def edge(source, targets, phase, evidence, origin='conservative', unresolved=False):
        targets = sorted(set(targets))
        if not targets and not unresolved:
            return
        edges.append({'from': source, 'targets': targets, 'phase': phase, 'origin': origin,
                      'resolution': 'unresolved' if unresolved else 'complete', 'evidence': evidence})
    def gap(source, key, kind, phase, reason):
        key = node(ident('gap', key), kind, 'qualification/' + key,
                   reason=reason, unresolved=True)
        edge(source, [key], phase, 'qualification/' + key)
        return key

    members = defaultdict(list)
    native = {r['id']: r for r in image['functions']}
    compiled = {r['id']: r for r in observed['nodes']}
    for f in image['functions']:
        key = node(ident('native', f['id']), 'function', 'image/functions/' + str(f['id']),
                   'retained native code prototype',
                   'Native identity only; no Wasm implementation or complete native call graph claimed.')
        members['@clean-image'].append(key)
        if f['source']:
            members[module(f['source'])].append(key)
        edge(key, [ident('native', t) for t in f['literal_functions']], 'run',
             'image/literals/' + str(f['id']), origin='observed')
    for f in observed['nodes']:
        key = node(ident('compiled', f['id']), 'function', 'r7/nodes/' + str(f['id']),
                   'retained native front-end body; not an emitted Wasm function')
        for source in f['sources']:
            members[module(source)].append(key)
        edge(key, [ident('operator', op) for op in f['operators']], 'compile',
             'r7/operators/' + str(f['id']), origin='observed')
    bindings = {}
    missing = []
    for b in candidates['global_bindings']:
        key = node(ident('binding', b['name']), 'function', 'candidates/binding/' + b['name'],
                   'source/native binding candidates',
                   'Union of source versions and snapshot bindings, not a past installation identity.')
        targets = [ident('compiled', f) for f in b['compiler_functions']]
        targets += [ident('native', f['function']) for f in b['native_bindings']]
        bindings[b['name']] = key
        if not targets:
            # Source-definition locations are useful leads, not proof that a
            # generic/accessor binding was installed or a conditional is dead.
            locations = sorted({loc['source'] for d in observed['source_definitions']
                                if d['name'] == b['name'] for loc in d['locations']
                                if loc['source']})
            missing.append({'name': b['name'], 'definition_modules': locations})
            targets = [ident('module', m) for m in locations]
        edge(key, targets, 'run', 'candidates/targets/' + b['name'], unresolved=True)
    seed_ids = []
    seed_names = {}
    for s in candidates['seeds']:
        key = ident('native', s['native_function'])
        seed_ids.append(key)
        seed_names[s['name']] = key
        if s['name'] in bindings:
            edge(key, [bindings[s['name']]], s['phase'], 'seeds/binding/' + s['name'])
    rebuild = seed_names['CCL::REBUILD-CCL']
    restore = seed_names['CCL::RESTORE-LISP-POINTERS']
    # Widen to the entire observed image and each captured source compilation.
    # These real surfaces compress the finite candidate set; they do NOT turn
    # it into a proved bound on future loading, EVAL or binding changes.
    sources = {module(s) for f in observed['nodes'] for s in f['sources']}
    sources.update(r['module'] for rows in (effects['compile'], effects['load']) for r in rows)
    edge(rebuild, [ident('module', s) for s in sorted(sources)], 'compile', 'r7/observed-rebuild-sources')
    edge(restore, [ident('module', '@clean-image')], 'load', 'image/whole-resident-surface')

    dynamic_surface = [ident('module', s) for s in sorted(sources | {'@clean-image'})]
    for kind in ('calls', 'function_references'):
        for index, call in enumerate(observed[kind]):
            targets = []
            for target in call['dependency']['targets']:
                targets.append(ident('compiled', target['id']) if target['kind'] == 'function'
                               else bindings[target['name']])
            edge(ident('compiled', call['caller']), targets or dynamic_surface,
                 'run', f'r7/{kind}/{index}', origin='observed' if targets else 'conservative',
                 unresolved=not bool(targets))
    gap(restore, 'candidate-bound', 'function', 'run',
        'Resident code plus compiled bodies is a retained candidate set. Future generation, '
        'loading, rebinding and native calls not captured as afuncs are not bounded.')
    gap(restore, 'seed-review', 'function', 'load', seeds['review_disposition'])

    # Actual evaluated dispatch identity is a proved join. A dispatch-table
    # entry is not proof of which templates its implementation may emit.
    templates = [ident('vinsn', v['name']) for v in lowering]
    for op in image['operators']:
        key = node(ident('operator', op['id']), 'operator', 'image/operators/' + str(op['id']),
                   'evaluated native operator slot',
                   'Reserved slot' if op['name'] is None else op['name'])
        edge(rebuild, [key], 'compile', 'image/evaluated-operator-inventory')
        if op['function'] is not None:
            handler = node(ident('handler', op['id']), 'handler', 'image/dispatch/' + str(op['id']),
                           op['handler'])
            edge(key, [handler], 'compile', 'image/operator-handler/' + str(op['id']), origin='observed')
            edge(handler, [ident('native', op['function'])], 'compile',
                 'image/handler-code/' + str(op['id']), origin='observed')
            edge(handler, templates, 'compile', 'lowering/whole-native-template-candidates/' + str(op['id']),
                 unresolved=True)
        elif op['name'] is not None:
            gap(key, 'operator-handler-' + str(op['id']), 'handler', 'compile',
                'Named slot has no native dispatch entry; rewrite-only/dead-slot proof is absent.')
    lap = {}
    for row in lowering:
        v = node(ident('vinsn', row['name']), 'vinsn', 'image/vinsns/' + row['name'],
                 'evaluated native template' if row['defined'] else None,
                 unresolved=not row['defined'])
        for op in row['opcodes']:
            key = ident('lap', op[0])
            if key not in lap:
                lap[key] = op[1:]
                node(key, 'lap', 'image/evaluated-opcode/' + str(op[0]), repr(op[1:]))
            elif lap[key] != op[1:]:
                raise ValueError('evaluated opcode identity conflict')
            edge(v, [key], 'compile', 'lowering/opcode/' + row['name'] + '/' + str(op[0]), origin='observed')
    for key, op in lap.items():
        if op[0].startswith('UUO-'):
            trap = node(ident('trap', op[0]), 'trap', 'image/opcode/' + op[0],
                        'native UUO opcode', 'Wasm condition/restart disposition remains unqualified.')
            edge(key, [trap], 'run', 'lowering/native-trap/' + op[0], origin='observed')
    subprims = []
    for sub in image['subprimitives']:
        key = node(ident('subprimitive', sub['name']), 'subprimitive', 'image/subprimitives/' + sub['name'],
                   'native table offset ' + str(sub['offset']))
        subprims.append(key)
    edge(rebuild, subprims, 'compile', 'image/evaluated-subprimitive-inventory')
    # Do not mistake :SET (register dataflow) for memory stores, or a UUO name
    # for a qualified Lisp-condition lowering. These missing joins stay visible.
    gap(rebuild, 'subprimitive-callers', 'subprimitive', 'compile', 'Template operands to concrete subprimitive/Lisp cycles are not joined.')
    gap(rebuild, 'imports', 'import', 'run', 'Kernel imports and direct foreign-call targets need evaluated caller/profile joins.')
    gap(rebuild, 'stores', 'store', 'compile', 'Pointer-store classes need evaluated operand/lowering joins; native :SET attributes alone do not classify stores.')
    gap(rebuild, 'wasm-dispositions', 'handler', 'compile', 'Native code locations are not complete Wasm implementation/replacement/condition dispositions.')
    gap(rebuild, 'macroexpand-dependencies', 'function', 'macroexpand',
        'Printed read/macroexpand previews do not provide complete identity-bearing expansion dependencies.')
    traced = node(ident('module', '@r5-traced-image'), 'module', 'trace/pinned-r5-image',
                  'retained r5 clean native image',
                  'Separate from the r7 inspected image; equal source revision is not identical heap state.')
    edge(restore, [traced], 'load', 'trace/r5-to-r7-scenario-join', unresolved=True)

    for row in effects['compile']:
        key = node(ident('init-compile', row['enter']), 'initializer', 'r7/event/' + str(row['enter']),
                   reason='Return observed; semantic state prerequisites and complete effect dependencies unproved.', unresolved=True)
        members[row['module']].append(key)
        edge(key, [ident('compiled', f) for f in row['compiled_during']], 'compile',
             'effects/compiled-during/' + str(row['enter']), origin='observed')
        initializers.append({'node': key, 'prerequisites': [], 'rank': 0,
                             'completion_assertion': 'Observed return at r7 event ' + str(row['return']) + '; prerequisites NOT_PROVED.'})
    for row in effects['load']:
        key = node(ident('init-load', row['sequence']), 'initializer', 'r7/event/' + str(row['sequence']),
                   reason='Emitted only; execution, prerequisite state and exact installed body are not observed.', unresolved=True)
        members[row['module']].append(key)
        edge(key, [ident('module', row['module'])], 'load', 'effects/load-body-candidates/' + str(row['sequence']), unresolved=True)
        initializers.append({'node': key, 'prerequisites': [], 'rank': 0,
                             'completion_assertion': 'NOT_OBSERVED: compiler emission is not loader completion.'})
    prior = None
    # Source control flow, not a chronological guess: these four calls precede
    # the callback DOLISTs in pristine U1 restore-lisp-pointers.
    pre = ['CCL::%REVIVE-SYSTEM-LOCKS', 'CCL::REFRESH-EXTERNAL-ENTRYPOINTS',
           'CCL::RESTORE-PASCAL-FUNCTIONS', 'CCL::INITIALIZE-INTERACTIVE-STREAMS']
    for rank, name in enumerate(pre, 1):
        key = node(ident('init-pre', name), 'initializer', 'U1/lib/dumplisp.lisp/restore-lisp-pointers',
                   implementation='native pre-callback function ' + name,
                   reason='Normal return inferred from reaching the first callback: these calls precede the callback restart scopes in pinned U1.')
        edge(restore, [key], 'load', 'startup/pre-callback/' + name)
        edge(key, [seed_names[name]], 'load', 'startup/pre-callback-body/' + name)
        initializers.append({'node': key, 'prerequisites': [prior] if prior else [], 'rank': rank,
                             'completion_assertion': 'INFERRED_FROM_SOURCE: first callback entry at cold event ' +
                             str(effects['startup'][0]['enter']) + ' requires this preceding call to have returned normally.'})
        prior = key
    for rank, row in enumerate(effects['startup'], len(pre) + 1):
        key = node(ident('init-startup', row['enter']), 'initializer', 'cold/event/' + str(row['enter']),
                   'native callback ' + str(row['function']), 'Normal-return ordering follows U1 callback traversal; no inferred data-dependency minimum.')
        edge(restore, [key], 'callback', 'startup/callback/' + str(row['enter']), origin='observed')
        edge(key, [ident('native', row['function'])], 'callback', 'startup/code/' + str(row['enter']), origin='observed')
        initializers.append({'node': key, 'prerequisites': [prior], 'rank': rank,
                             'completion_assertion': 'Normal return witnessed at cold event ' + str(row['return'])})
        prior = key

    stub_module = '@census-stub-corpus'
    stub_bindings = set()
    def stub_function(f):
        key = node(ident('stub', f['function_id']), 'function', 'stub/functions/' + str(f['function_id']),
                   'registered Wasm target front-end capture; no executable output')
        members[stub_module].append(key)
        edge(key, [ident('operator', op['id']) for op in f['operators']], 'compile',
             'stub/operator-slots/' + str(f['function_id']), origin='observed')
        for kind in ('calls', 'function_references'):
            for index, call in enumerate(f[kind]):
                targets = []
                for target in call['dependency']['targets']:
                    if target['kind'] == 'function':
                        targets.append(ident('stub', target['id']))
                    elif target['name'] in bindings:
                        targets.append(bindings[target['name']])
                    else:
                        binding = ident('stub-binding', target['name'])
                        if binding not in stub_bindings:
                            node(binding, 'function', 'stub/binding/' + target['name'],
                                 reason='Fixture external binding; no implementation emitted.', unresolved=True)
                            stub_bindings.add(binding)
                        targets.append(binding)
                edge(key, targets or dynamic_surface, 'run', f'stub/{kind}/{f["function_id"]}/{index}',
                     origin='observed' if targets else 'conservative', unresolved=not bool(targets))
        for child in f['inner_functions']:
            stub_function(child)
    for row in stub['rows']:
        stub_function(row['function'])
    edge(rebuild, [ident('module', stub_module)], 'compile', 'stub/accepted-fourteen-form-corpus')
    gap(rebuild, 'target-source-coverage', 'function', 'compile',
        'Accepted LL08-a captures fourteen forms; no complete U1 source traversal under Wasm target state is retained.')
    for source, children in sorted(members.items()):
        key = node(ident('module', source), 'module', 'members/' + source, 'retained observation surface ' + source,
                   'Conservative whole-module candidates, including inspector code where present.')
        edge(key, children, 'compile' if source != '@clean-image' else 'load', 'members/' + source)
        # Preserve function->source/module joins, not merely labels on nodes.
        for child in sorted(set(children)):
            edge(child, [key], 'compile', 'provenance/' + source + '/' + child)
    graph = {'version': 1, 'source_revision': BASELINE,
             'profile': 'UNQUALIFIED native observation projection plus fourteen Wasm target front-end forms; NOT a qualified Wasm closure',
             'instrumentation_sha256': identities['instrumentation'], 'inputs_sha256': identities['inputs'],
             'trace_sha256': identities['trace'], 'seed_review': seeds['review_disposition'],
             'seeds': seed_ids, 'nodes': list(nodes.values()), 'edges': edges,
             'initializers': initializers, 'observed_modules': [traced],
             'unobserved_modules': []}
    reachable = fixed_point(graph)
    graph['unobserved_modules'] = [{'node': key, 'reason':
        'Static/compiled/resident source surface retained. The separate --no-init image-start trace opens the image, not this source or a FASL.'}
        for key, n in nodes.items() if key in reachable and n['kind'] == 'module' and key not in graph['observed_modules']]
    return graph, {'missing_named_candidates': missing, 'effects': effects, 'lowering': lowering,
                   'scope': 'Witness joins and unresolved work; no acceptance result.'}
