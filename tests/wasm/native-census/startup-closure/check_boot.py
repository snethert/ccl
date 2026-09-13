"""Independent full-record bounds for the boot fragment, from retained inputs."""
from collections import Counter
from boot_join import canonical, key


def expectations(base, rows, boot, files, origins, binding):
    """Derive by relation families, without invoking the graph producer."""
    nodes, edges = {}, []
    def n(i, kind, implementation, evidence, reason='', unresolved=False):
        record = {'id': i, 'kind': kind, 'disposition': 'unresolved' if unresolved else 'implemented',
                  'required': True, 'implementation': implementation, 'evidence': evidence,
                  'reason': reason, 'tests': ['S0-LL15-b', 'S0-LL15-c']}
        if i in nodes and nodes[i] != record: raise ValueError('ORACLE_NODE_CONFLICT')
        nodes[i] = record
    def e(source, targets, evidence, conservative=False):
        edges.append({'from': source, 'targets': sorted(set(targets)), 'phase': 'load',
                      'origin': 'conservative' if conservative else 'observed',
                      'resolution': 'complete', 'evidence': evidence})
    surface = key('module', '@execution')
    scope = 'Observed boot event boundaries, binding states and cold source origins; not static dependency closure or Wasm implementation.'
    n(surface, 'module', 'Separate reviewed native boot process', 'boot/capture', scope)
    n(key('gap', 'closure'), 'function', None, 'boot/scope',
      'Full target traversal, calls, opaque value contents and Wasm dispositions remain unqualified.', True)
    e('identity:build:gap:boot-process', [surface], 'boot/separate-process-witness', True)
    e(surface, [key('gap', 'closure')], 'boot/dependency-closure', True)
    events = [r for r in rows if 'sequence' in r]
    active = [{'family': r['family'], 'enter': r['enter']} for r in boot['handoff']]
    initializers = []
    for event in events:
        seq, kind = event['sequence'], event['kind']
        n(key('event', seq), 'initializer', 'Observed native ' + kind + ' boundary',
          'boot/event/' + str(seq), canonical(event['payload']))
        assertion = 'Observed native ' + kind + ' boundary at event ' + str(seq) + '.'
        if kind in ('load-enter', 'reader-enter', 'call-enter', 'cold-enter'):
            assertion += ' Entry witnessed; this assertion does not claim its return.'
        if kind == 'binding-removing':
            assertion += ' Pre-clear intent; subsequent replay and final checkpoint are separate witnesses.'
        if kind == 'handoff':
            assertion += ' Still active, with no recorded returns: ' + canonical(active) + '.'
        initializers.append({'node': key('event', seq), 'prerequisites': [key('event', seq - 1)] if seq > 1 else [],
                             'rank': seq, 'completion_assertion': assertion})
    e(surface, [key('event', r['sequence']) for r in events], 'boot/event-coverage')
    by_file = {r['file']: r for r in files['files']}
    for path in sorted({r['relative_path'] for r in files['files']}):
        aliases = sorted((r for r in files['files'] if r['relative_path'] == path), key=lambda r:r['file'])
        if any((r['sha256'], r['bytes']) != (aliases[0]['sha256'], aliases[0]['bytes']) for r in aliases):
            raise ValueError('FILE_ALIAS_BYTES')
        n(key('fasl', path), 'module', 'Retained boot loader input',
          'boot/files/' + path, canonical(aliases))
    ids = {r['id']: r for r in base['nodes']}
    for r in origins['sources']:
        prior = key('source', r['path']).replace('boot:source:', 'module:', 1)
        if ids.get(prior, {}).get('kind') != 'module': raise ValueError('SOURCE_INVENTORY_MEMBERSHIP')
        n(key('source', r['path']), 'module', 'Source bytes bound by reviewed xload origin witness',
          'boot/origin-sources/' + r['path'], canonical(r))
        e(prior, [key('source', r['path'])], 'boot/source-inventory-path/' + r['path'], True)
    referenced, symbols, tables = set(), set(), set()
    for family in ('cold_initializers', 'loads', 'readers', 'calls', 'handoff'):
        for r in boot[family]:
            for seq in [r['enter']] + ([r['return']] if 'return' in r else []):
                current = key('event', seq)
                if r['parent'] is not None: e(current, [key('event', r['parent'])], 'boot/enclosing/' + str(seq))
                if 'file' in r: e(current, [key('fasl', by_file[r['file']]['relative_path'])], 'boot/file/' + str(seq))
                if 'table' in r:
                    tables.add(r['table']); e(current, [key('table', r['table'])], 'boot/table/' + str(seq))
                for role in ('function', 'reader'):
                    if role in r:
                        referenced.add(r[role]); e(current, [key('object', r[role])], 'boot/' + role + '/' + str(seq))
    for r in boot['bindings']:
        seq = r['event']; symbols.add(r['symbol'])
        e(key('event', seq), [key('cell', r['symbol'])], 'boot/cell/' + str(seq))
        for role in ('old', 'new'):
            referenced.add(r[role]); e(key('event', seq), [key('object', r[role])], 'boot/' + role + '/' + str(seq))
        if r['parent'] is not None: e(key('event', seq), [key('event', r['parent'])], 'boot/enclosing/' + str(seq))
    for label in ('initial', 'final'):
        for r in boot[label + '_bindings']:
            symbols.add(r['symbol']); referenced.add(r['value'])
            e(key('cell', r['symbol']), [key('object', r['value'])], 'boot/' + label + '-binding/' + str(r['symbol']))
    descriptions = {r['id']: r for r in boot['objects']}
    for i in referenced:
        r = descriptions[i]; opaque = r['kind'] == 'opaque'
        n(key('object', i), 'function' if r['kind'] == 'function' else 'store',
          None if opaque else 'Recorded native ' + r['kind'] + ' identity', 'boot/objects/' + str(i), canonical(r), opaque)
    for i in symbols:
        n(key('cell', i), 'store', 'Observed native function cell', 'boot/symbols/' + str(i), canonical(descriptions[i]))
    for i in tables:
        n(key('table', i), 'store', 'Observed reader dispatch table identity', 'boot/table/' + str(i),
          'Identity only; table contents are not enumerated by this event slice.')
    for r, effect in zip(origins['entries'], boot['cold_initializers']):
        if r['boot_function'] != effect['function']: raise ValueError('COLD_ORIGIN_ORDER')
        label = 'boot/cold-origin/' + str(r['position'])
        e(key('object', effect['function']), [key('source', r['source'])], label)
        e(key('event', effect['enter']), [key('source', r['source'])], label + '/entry')
    if len(origins['entries']) != len(boot['cold_initializers']): raise ValueError('COLD_ORIGIN_COUNT')
    return {'version': 1, 'scope': scope, 'input_binding': binding, 'nodes': nodes,
            'edges': Counter(canonical(r) for r in edges), 'initializers': initializers,
            'unobserved_modules': [{'node': i, 'reason': 'Separate boot/xload witness; not a file observation in the original external clean-image trace.'}
                                   for i in sorted(nodes) if nodes[i]['kind'] == 'module'],
            'cold_origins': origins['entries'], 'active_handoff': active}


def check(delta, expected):
    def require(ok, reason):
        if not ok: raise ValueError(reason)
    require(set(delta) == set(expected), 'FRAGMENT_FIELDS')
    for k in ('version', 'scope', 'input_binding'):
        require(delta[k] == expected[k], 'FRAGMENT_' + k.upper())
    nodes = {r['id']: r for r in delta['nodes']}
    require(len(nodes) == len(delta['nodes']), 'DUPLICATE_NODE')
    require(nodes == expected['nodes'], 'NODE_RECORDS')
    require(Counter(canonical(r) for r in delta['edges']) == expected['edges'], 'EDGE_RECORDS')
    require(delta['initializers'] == expected['initializers'], 'INITIALIZER_RECORDS')
    require(delta['unobserved_modules'] == expected['unobserved_modules'], 'MODULE_RECORDS')
    require(delta['cold_origins'] == expected['cold_origins'], 'COLD_ORIGIN_RECORDS')
    require(delta['active_handoff'] == expected['active_handoff'], 'HANDOFF_RECORDS')
    return {'status': 'PASS'}


def check_materialized(base, graph, delta):
    fields = ('nodes', 'edges', 'initializers', 'unobserved_modules')
    if set(graph) != set(base): raise ValueError('GRAPH_FIELDS')
    for k in fields:
        if graph[k][:len(base[k])] != base[k] or graph[k][len(base[k]):] != delta[k]:
            raise ValueError('GRAPH_' + k.upper())
    for k in set(base) - set(fields) - {'profile'}:
        if graph[k] != base[k]: raise ValueError('GRAPH_' + k.upper())
    if graph['profile'] != base['profile'] + '; separate native boot execution and source origins (closure unqualified)':
        raise ValueError('GRAPH_PROFILE')
    if {r['id'] for r in base['nodes']} & {r['id'] for r in delta['nodes']}:
        raise ValueError('NODE_NAMESPACE_COLLISION')
