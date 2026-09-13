"""Add reviewed execution identities to the exchange graph without merging runs."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json

from exchange import ident, fixed_point
from effects import module

PREFIX = 'identity:'
TESTS = ['S0-LL15-b', 'S0-LL15-c']


def key(stream, kind, value):
    return PREFIX + stream + ':' + ident(kind, value)


def value_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def prepare(data):
    """Check execution/value identities before giving any boundary a completion."""
    effects = {e['enter']: e for e in data['effects']}
    if len(effects) != len(data['effects']):
        raise ValueError('duplicate effect identity')
    calls = {}
    materialized = {r['function']: r['afunc'] for r in data['materialized']}
    reads = {r['function']: r for r in data['fasl_reads']}
    values = defaultdict(list)
    for row in data['effect_values']:
        values[row['parent']].append(row)
    for family, rows in [('compile', data['compile_calls']), ('load', data['load_calls'])]:
        for row in rows:
            effect = effects[row['initializer']]
            parent = row['initializer'] if family == 'compile' else row['event']
            returned = values[parent]
            if len(returned) != 1 or returned[0]['function'] != row['function']:
                raise ValueError('initializer result ownership differs from its callee')
            returned = returned[0]
            if not effect['enter'] < row['event'] < returned['event'] < effect['return']:
                raise ValueError('initializer call/value outside its completion boundaries')
            if family == 'compile':
                if effect['family'] != 'compile-initializer' or row['function'] not in materialized:
                    raise ValueError('compile initializer lacks exact materialization')
            else:
                if effect['family'] != 'fasl-effect' or effect['reader_mode'] != 'native':
                    raise ValueError('Lisp loader execution assigned to an image builder')
                read = reads.get(row['function'])
                if not read or not read['written'] or read['written']['function'] not in materialized:
                    raise ValueError('loader initializer lacks serialized materialization')
                if read['file'] != row['file'] or read['event'] >= row['event']:
                    raise ValueError('loader initializer has an inconsistent preceding read')
            if row['initializer'] in calls:
                raise ValueError('multiple initializer calls assigned to one effect')
            calls[row['initializer']] = {**row, 'family': family, 'value_event': returned['event'],
                                         'values_sha256': value_digest(returned['values'])}
    # Reconstruct the order independently of the previously computed schedule.
    boundaries = []
    for effect in data['effects']:
        for label, event in [('enter', effect['enter']), ('return', effect['return'])]:
            boundaries.append((event, effect['process'], label, effect))
    boundaries.sort(key=lambda r: r[0])
    previous = {}; expected = []
    for rank, (event, process, label, effect) in enumerate(boundaries):
        expected.append({'event': event, 'phase': effect['family'] + '-' + label, 'process': process,
                         'prerequisite_boundary': previous.get(process), 'rank': rank})
        previous[process] = event
    if expected != data['effect_schedule']:
        raise ValueError('effect schedule differs from actual entry/return order')
    return effects, calls, materialized, reads, boundaries


def extend(base, streams, identities):
    graph = deepcopy(base)
    nodes = {n['id']: n for n in graph['nodes']}
    witnesses = {'version': 1, 'streams': {}, 'scope': 'Exact execution joins and conservative per-process order. No cross-run code identity or complete dependency bound.'}
    roots = {}
    for name in ('CCL::REBUILD-CCL', 'CCL::RESTORE-LISP-POINTERS'):
        roots[name] = next(e['from'] for e in base['edges'] if e['evidence'] == 'seeds/binding/' + name)

    def node(i, kind, evidence, implementation, reason='', unresolved=False):
        if i in nodes:
            return i
        n = {'id': i, 'kind': kind, 'disposition': 'unresolved' if unresolved else 'implemented',
             'required': True, 'implementation': implementation, 'evidence': evidence, 'tests': TESTS, 'reason': reason}
        graph['nodes'].append(n); nodes[i] = n
        return i

    def edge(source, targets, phase, evidence, origin='observed'):
        graph['edges'].append({'from': source, 'targets': sorted(set(targets)), 'phase': phase,
                               'origin': origin, 'resolution': 'complete', 'evidence': evidence})

    for stream, data in streams.items():
        effects, calls, materialized, reads, boundaries = prepare(data)
        surface = node(key(stream, 'module', '@execution'), 'module', stream + '/recorded-execution',
                       'Retained native process execution; separate identity namespace')
        root = roots['CCL::RESTORE-LISP-POINTERS' if stream == 'cold' else 'CCL::REBUILD-CCL']
        edge(root, [surface], 'callback' if stream == 'cold' else 'compile', stream + '/workload-surface', 'conservative')
        rows = []

        def function(code):
            return node(key(stream, 'code', code), 'function', f'{stream}/code/{code}',
                        'Recorded native callable code identity', 'Identity only; its full call dependencies are not established by this effect slice.')

        def body(code):
            f = function(code)
            if code in materialized:
                afunc = materialized[code]
                a = node(key(stream, 'afunc', afunc), 'function', f'{stream}/materialized/{code}',
                         'Recorded front-end function materialized as this native callable')
                evidence = f'{stream}/code-afunc/{code}'
                if evidence not in joined:
                    edge(f, [a], 'compile', evidence); joined.add(evidence)
            elif code in reads and reads[code]['written']:
                read = reads[code]; compiled = read['written']['function']
                evidence = f'{stream}/loaded-code/{code}'
                if evidence not in joined:
                    edge(f, [body(compiled)], 'load', evidence); joined.add(evidence)
            return f

        joined = set()
        callbacks = {r['initializer']: r for r in data.get('startup_calls', [])}
        preceding = {}
        for rank, (event, process, label, effect) in enumerate(boundaries, 1):
            mode = effect.get('reader_mode')
            family = effect['family']
            phase = 'compile' if family == 'compile-initializer' else 'callback' if family == 'startup' else 'load'
            i = node(key(stream, 'boundary', event), 'initializer', f'{stream}/event/{event}',
                     'Observed native ' + family + ' ' + label,
                     'Image-reader completion is not queued Lisp initializer execution.' if mode == 'cross-dump' else 'Conservative recorded event order, not minimal state read/write dependencies.')
            edge(surface, [i], phase, f'{stream}/effect-boundary/{event}')
            prerequisite = preceding.get(process)
            assertion = f'Observed {family} {label} at {stream} event {event}; process {process}.'
            if mode:
                assertion += ' Reader table: ' + mode + '.'
                edge(i, [body(effect['reader_function'])], 'load', f'{stream}/reader/{event}')
            if mode == 'cross-dump':
                assertion += ' Queued Lisp execution NOT_OBSERVED.'
            call = calls.get(effect['enter'])
            if call:
                edge(i, [body(call['function'])], phase, f'{stream}/callee/{event}')
                if label == 'return':
                    assertion += f' Callee {call["function"]}; values event {call["value_event"]}; values SHA256 {call["values_sha256"]}.'
            if effect['enter'] in callbacks:
                callback = callbacks[effect['enter']]
                edge(i, [body(callback['function'])], 'callback', f'{stream}/callback-code/{event}')
                assertion += f' Callback code {callback["function"]}; paired return {callback["return"]}.'
            graph['initializers'].append({'node': i, 'prerequisites': [prerequisite] if prerequisite else [],
                                           'rank': rank, 'completion_assertion': assertion})
            preceding[process] = i
            row = {'event': event, 'effect_enter': effect['enter'], 'process': process, 'label': label,
                   'family': family, 'source': effect['source'], 'reader_mode': mode}
            if call: row['call'] = call
            rows.append(row)
            if effect['source']:
                m = module(effect['source'])
                source_module = node(key(stream, 'module', m), 'module', f'{stream}/source/{m}',
                                     'Source surface recorded by this execution')
                edge(i, [source_module], phase, f'{stream}/source-module/{event}')

        # No per-function proof of static callees follows from recording its
        # initializer invocation. Keep this missing obligation reachable.
        gap = node(key(stream, 'gap', 'dependency-closure'), 'function', stream + '/scope', None,
                   'Execution identities and ordering do not supply complete static callees, seed review, or target dispositions.', True)
        edge(surface, [gap], 'run', stream + '/dependency-closure', 'conservative')
        if stream == 'build':
            gap = node(key(stream, 'gap', 'boot-process'), 'initializer', 'build/boot-process-not-observed', None,
                       'The boot-image subprocess did not load the observer. Its queued L1 installation needs a separate witness.', True)
            edge(surface, [gap], 'load', 'build/boot-process-required', 'conservative')
            graph['initializers'].append({'node': gap, 'prerequisites': [], 'rank': 0,
                                           'completion_assertion': 'NOT_OBSERVED: image-builder return is not boot-process Lisp execution.'})
        witnesses['streams'][stream] = {'boundaries': rows, 'calls': list(calls.values()),
                                       'callbacks': list(callbacks.values()),
                                       'reader_effects': dict(Counter(e.get('reader_mode') for e in effects.values() if e['family'] == 'fasl-effect'))}
    graph['profile'] = 'UNQUALIFIED native projection with separately scoped compiler/loader execution identities; NOT a qualified Wasm closure'
    graph['instrumentation_sha256'] = identities['instrumentation']
    graph['inputs_sha256'] = identities['inputs']
    reachable = fixed_point(graph)
    original_modules = {n['node'] for n in graph['unobserved_modules']} | set(graph['observed_modules'])
    graph['unobserved_modules'] += [{'node': n['id'], 'reason': 'Separate captured process/source surface; not a file open in the external clean-image trace.'}
                                   for n in graph['nodes'] if n['kind'] == 'module' and n['id'] in reachable and n['id'] not in original_modules]
    return graph, witnesses


def expected_additions(base, streams):
    """Bound the additions from capture records, independently of extend()."""
    nodes, edges, initializers, modules = {}, Counter(), set(), set()

    def node(i, kind):
        if i in nodes and nodes[i] != kind:
            raise ValueError('EXPECTED_NODE_KIND')
        nodes[i] = kind
        if kind == 'module': modules.add(i)
        if kind == 'initializer': initializers.add(i)
        return i

    def edge(source, target, phase, evidence, origin='observed'):
        edges[source, (target,), phase, origin, 'complete', evidence] += 1

    for stream, data in streams.items():
        surface = node(key(stream, 'module', '@execution'), 'module')
        root_name = 'CCL::RESTORE-LISP-POINTERS' if stream == 'cold' else 'CCL::REBUILD-CCL'
        root = next(e['from'] for e in base['edges'] if e['evidence'] == 'seeds/binding/' + root_name)
        edge(root, surface, 'callback' if stream == 'cold' else 'compile', stream + '/workload-surface', 'conservative')
        gap = node(key(stream, 'gap', 'dependency-closure'), 'function')
        edge(surface, gap, 'run', stream + '/dependency-closure', 'conservative')
        if stream == 'build':
            gap = node(key(stream, 'gap', 'boot-process'), 'initializer')
            edge(surface, gap, 'load', 'build/boot-process-required', 'conservative')
        calls = {r['initializer']: r['function'] for r in data['compile_calls'] + data['load_calls']}
        callbacks = {r['initializer']: r['function'] for r in data.get('startup_calls', [])}
        codes = set()
        for effect in data['effects']:
            phase = 'compile' if effect['family'] == 'compile-initializer' else 'callback' if effect['family'] == 'startup' else 'load'
            for event in (effect['enter'], effect['return']):
                boundary = node(key(stream, 'boundary', event), 'initializer')
                edge(surface, boundary, phase, f'{stream}/effect-boundary/{event}')
                if effect['source']:
                    source = node(key(stream, 'module', module(effect['source'])), 'module')
                    edge(boundary, source, phase, f'{stream}/source-module/{event}')
                references = []
                if effect.get('reader_mode'):
                    references.append(('reader', effect['reader_function'], 'load'))
                if effect['enter'] in calls:
                    references.append(('callee', calls[effect['enter']], phase))
                if effect['enter'] in callbacks:
                    references.append(('callback-code', callbacks[effect['enter']], 'callback'))
                for role, code, call_phase in references:
                    codes.add(code)
                    edge(boundary, key(stream, 'code', code), call_phase, f'{stream}/{role}/{event}')
        materialized = {r['function']: r['afunc'] for r in data['materialized']}
        reads = {r['function']: r for r in data['fasl_reads']}
        serialized = {code: r['written']['function'] for code, r in reads.items() if r['written']}
        pending, seen = list(codes), set()
        while pending:
            code = pending.pop()
            if code in seen: continue
            seen.add(code)
            current = node(key(stream, 'code', code), 'function')
            if code in materialized:
                target = node(key(stream, 'afunc', materialized[code]), 'function')
                edge(current, target, 'compile', f'{stream}/code-afunc/{code}')
            elif code in serialized:
                target = serialized[code]
                edge(current, key(stream, 'code', target), 'load', f'{stream}/loaded-code/{code}')
                pending.append(target)
    return nodes, edges, initializers, modules


def check(base, graph, witnesses, streams):
    """Check original coverage plus literal code/value witnesses from each capture."""
    def require(ok, code):
        if not ok: raise ValueError(code)
    for field in ('nodes', 'edges', 'initializers', 'unobserved_modules'):
        require(graph[field][:len(base[field])] == base[field], 'ORIGINAL_' + field.upper())
    require(graph['seeds'] == base['seeds'] and graph['seed_review'] == base['seed_review'], 'SEED_PRESERVATION')
    require(graph['observed_modules'] == base['observed_modules'] and graph['trace_sha256'] == base['trace_sha256'], 'TRACE_PRESERVATION')
    nodes = {r['id']: r for r in graph['nodes']}
    require(len(nodes) == len(graph['nodes']), 'DUPLICATE_NODE')
    require(all(n['required'] for n in graph['nodes'][len(base['nodes']):]), 'REQUIRED_SCOPE')
    init = {r['node']: r for r in graph['initializers']}
    require(len(init) == len(graph['initializers']), 'DUPLICATE_INITIALIZER')
    edges = defaultdict(list)
    for e in graph['edges']: edges[e['evidence']].append(e)
    def one(evidence, source, target, phase=None):
        rows = edges[evidence]
        require(len(rows) == 1 and rows[0]['from'] == source and rows[0]['targets'] == [target]
                and rows[0]['resolution'] == 'complete' and rows[0]['origin'] == 'observed', 'EXACT_EDGE:' + evidence)
        if phase is not None: require(rows[0]['phase'] == phase, 'EDGE_PHASE')
    for stream, data in streams.items():
        expected = {r[field] for r in data['effects'] for field in ('enter', 'return')}
        require({i for i in nodes if i.startswith(key(stream, 'boundary', ''))} ==
                {key(stream, 'boundary', e) for e in expected}, 'BOUNDARY_COVERAGE')
        witness = witnesses['streams'][stream]
        require({r['event'] for r in witness['boundaries']} == expected and len(witness['boundaries']) == len(expected), 'WITNESS_COVERAGE')
        ordered = sorted((r[field], r, field) for r in data['effects'] for field in ('enter', 'return'))
        previous = {}; call_rows = {r['initializer']: r for r in data['compile_calls'] + data['load_calls']}
        values = {r['parent']: r for r in data['effect_values']}
        materialized = {r['function']: r['afunc'] for r in data['materialized']}
        reads = {r['function']: r for r in data['fasl_reads']}
        callbacks = {r['initializer']: r for r in data.get('startup_calls', [])}
        require(witness['callbacks'] == list(callbacks.values()), 'CALLBACK_WITNESS')
        require(witness['reader_effects'] == dict(Counter(e.get('reader_mode') for e in data['effects'] if e['family'] == 'fasl-effect')), 'READER_WITNESS')
        witness_rows = {r['event']: r for r in witness['boundaries']}
        witness_calls = {r['initializer']: r for r in witness['calls']}
        require(set(witness_calls) == set(call_rows) and len(witness['calls']) == len(call_rows), 'CALL_WITNESS')
        for rank, (event, effect, label) in enumerate(ordered, 1):
            i = key(stream, 'boundary', event)
            require(i in init and init[i]['rank'] == rank and init[i]['prerequisites'] ==
                    ([previous[effect['process']]] if effect['process'] in previous else []), 'EFFECT_ORDER')
            previous[effect['process']] = i
            phase = 'compile' if effect['family'] == 'compile-initializer' else 'callback' if effect['family'] == 'startup' else 'load'
            one(f'{stream}/effect-boundary/{event}', key(stream, 'module', '@execution'), i, phase)
            require(nodes[i]['disposition'] == 'implemented' and nodes[i]['implementation'] == 'Observed native ' + effect['family'] + ' ' + label, 'BOUNDARY_CLAIM')
            mode = effect.get('reader_mode')
            wr = witness_rows[event]
            require({k: v for k, v in wr.items() if k != 'call'} == {'event': event, 'effect_enter': effect['enter'], 'process': effect['process'], 'label': label, 'family': effect['family'], 'source': effect['source'], 'reader_mode': mode}, 'BOUNDARY_WITNESS')
            if mode:
                one(f'{stream}/reader/{event}', i, key(stream, 'code', effect['reader_function']), 'load')
                require('Reader table: ' + mode + '.' in init[i]['completion_assertion'], 'READER_MODE')
            if mode == 'cross-dump': require('Queued Lisp execution NOT_OBSERVED.' in init[i]['completion_assertion'], 'IMAGE_EXECUTION_PROMOTION')
            if effect['enter'] in callbacks:
                c = callbacks[effect['enter']]
                one(f'{stream}/callback-code/{event}', i, key(stream, 'code', c['function']), 'callback')
                require(c['return'] == effect['return'] and
                        f'Callback code {c["function"]}; paired return {c["return"]}.' in init[i]['completion_assertion'], 'CALLBACK_WITNESS')
            if effect['enter'] in call_rows:
                c = call_rows[effect['enter']]; code = c['function']
                v = values[effect['enter'] if effect['family'] == 'compile-initializer' else c['event']]
                expected_call = {**c, 'family': 'compile' if effect['family'] == 'compile-initializer' else 'load', 'value_event': v['event'], 'values_sha256': value_digest(v['values'])}
                require(witness_calls[effect['enter']] == expected_call and wr.get('call') == expected_call, 'CALL_WITNESS')
                one(f'{stream}/callee/{event}', i, key(stream, 'code', code), phase)
                if code in materialized:
                    one(f'{stream}/code-afunc/{code}', key(stream, 'code', code), key(stream, 'afunc', materialized[code]), 'compile')
                else:
                    r = reads[code]; compiled = r['written']['function']
                    one(f'{stream}/loaded-code/{code}', key(stream, 'code', code), key(stream, 'code', compiled), 'load')
                    one(f'{stream}/code-afunc/{compiled}', key(stream, 'code', compiled), key(stream, 'afunc', materialized[compiled]), 'compile')
                if label == 'return':
                    v = values[effect['enter'] if effect['family'] == 'compile-initializer' else c['event']]
                    require(f'Callee {code}; values event {v["event"]}; values SHA256 {value_digest(v["values"])}.' in init[i]['completion_assertion'], 'RESULT_WITNESS')
        gap = key(stream, 'gap', 'dependency-closure')
        require(gap in nodes and nodes[gap]['disposition'] == 'unresolved' and nodes[gap]['implementation'] is None, 'DEPENDENCY_SCOPE')
    boot = key('build', 'gap', 'boot-process')
    require(boot in nodes and nodes[boot]['disposition'] == 'unresolved' and 'NOT_OBSERVED' in init[boot]['completion_assertion'], 'BOOT_SCOPE')
    expected_nodes, expected_edges, expected_init, expected_modules = expected_additions(base, streams)
    added_nodes = {n['id']: n['kind'] for n in graph['nodes'][len(base['nodes']):]}
    require(added_nodes == expected_nodes, 'ADDED_NODES')
    # Count full relations, including evidence identity and multiplicity. Merely
    # checking evidence names would miss a changed endpoint on an unchecked edge.
    added_edges = Counter((e['from'], tuple(e['targets']), e['phase'], e['origin'], e['resolution'], e['evidence'])
                          for e in graph['edges'][len(base['edges']):])
    require(added_edges == expected_edges, 'ADDED_EDGES')
    require({i['node'] for i in graph['initializers'][len(base['initializers']):]} == expected_init, 'ADDED_INITIALIZERS')
    require(Counter(m['node'] for m in graph['unobserved_modules'][len(base['unobserved_modules']):]) ==
            Counter({i: 1 for i in expected_modules}), 'ADDED_MODULES')
    return {'status': 'PASS', 'scope': 'Execution identity/order integration; full census remains unqualified.'}
