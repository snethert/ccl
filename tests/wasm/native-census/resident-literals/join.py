"""Exact initial-inventory literal dependencies; never a method/callee bound."""
from collections import Counter
import hashlib
import json

SCOPE = 'Original native inventory function references and reported U1 source extents; no callable-subtype, construction, IR-body or exhaustive callee claim.'
PREFIX = 'identity:build:code:'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(event, process):
    require(event['kind'] == 'resident-function' and event['process'] == process
            and event['payload']['stage'] == 'before', 'INVENTORY_CONTEXT')
    graph = event['payload']['function']
    require(len(graph['objects']) == 1, 'DESCRIPTOR_GRAPH')
    fn = graph['objects'][0]
    require(fn['kind'] == 'function' and type(fn['code']) is int
            and fn['id'] == fn['code'] and graph['root'] == {'ref': fn['id']}, 'FUNCTION_IDENTITY')
    literals = event['payload']['literal_functions']
    require(isinstance(literals, list) and all(type(c) is int and c > 0 for c in literals)
            and len(literals) == len(set(literals)), 'LITERAL_IDENTITY_SET')
    return fn, literals


def collect(origins, witnesses, prefix, export, summary, sources):
    # The reviewed complete read-only prefix is the ONLY cross-execution anchor.
    # Ignore the fresh capture's dynamic suffix, even if a printed name agrees.
    n = summary['readonly_functions']
    require(len(prefix) >= n + 2 and sha(b''.join(prefix[:n+2])) == summary['original_prefix_sha256'],
            'ORIGINAL_READONLY_PREFIX')
    rows = [json.loads(line) for line in prefix[:n+2]]
    require(rows[0]['kind'] == 'snapshot' and rows[1]['kind'] == 'inventory-enter'
            and rows[1]['payload'] == {'stage': 'before'}, 'PREFIX_START')
    process = rows[1]['process']
    require(export['version'] == 1 and export['area'] == 'readonly'
            and len(export['functions']) == n, 'READONLY_EXPORT')
    readonly = {}
    for i, (event, live) in enumerate(zip(rows[2:], export['functions'])):
        fn, literals = descriptor(event, process)
        require(event['sequence'] == i+3 and live['ordinal'] == i
                and live['id'] == fn['id'] and live['code'] == fn['code']
                and live['description'] == fn['description'] and fn['code'] not in readonly,
                'READONLY_EXPORT_IDENTITY')
        readonly[fn['code']] = (event, live)
    raw = {json.loads(line)['sequence']: (json.loads(line), sha(line)) for line in witnesses}
    require(len(raw) == len(witnesses), 'WITNESS_EVENT_DUPLICATE')
    selected = [r for r in origins['prototypes'] if r['category'] == 'INITIAL_INVENTORY_OUTSIDE_READONLY'
                and r['first_called_binding']['value']['description']['source'] is None]
    roots = {}
    for r in selected:
        c = r['code']; first = r['first_descriptor']; pair = raw.get(first['event']['sequence'])
        require(pair is not None and pair[1] == first['event_sha256'], 'ORIGIN_EVENT_JOIN')
        event = pair[0]
        require(all(event[k] == v for k, v in first['event'].items()), 'ORIGIN_EVENT_CONTEXT')
        fn, literals = descriptor(event, process)
        require(fn['code'] == c and fn['description']['source'] is None
                and first['descriptors'] == [{'path': ['payload', 'function', 'objects', 0], 'value': fn}],
                'ORIGIN_FUNCTION_JOIN')
        require(r['initial_residents'] == [{'event': event['sequence'], 'stage': 'before', 'code': c, 'object': fn['id']}],
                'ORIGIN_INVENTORY_JOIN')
        require(c not in readonly and c not in roots, 'ROOT_IDENTITY_SET')
        roots[c] = event
    require(roots, 'EMPTY_ROOT_SET')
    pending = list(sorted(roots)); records = {}; source_records = []
    paths = {'ccl:l1;l1-dcode.lisp.newest': 'level-1/l1-dcode.lisp',
             'ccl:lib;describe.lisp.newest': 'lib/describe.lisp'}
    while pending:
        c = pending.pop()
        if c in records:
            continue
        require(c in roots or c in readonly, 'UNANCHORED_LITERAL_TARGET')
        event = roots[c] if c in roots else readonly[c][0]
        fn, literals = descriptor(event, process)
        records[c] = dict(code=c, inventory_event=event, descriptor=fn,
                          literal_codes=sorted(literals), root=c in roots,
                          callable_subtype='UNCLASSIFIED', exhaustive_callees=False, complete_ir_body=False)
        if c not in roots:
            live = readonly[c][1]; desc = fn['description']
            path = paths.get(desc['source']); start = desc['position']; end = live['source_end']
            require(path in sources and type(start) is int and type(end) is int
                    and 0 <= start < end <= len(sources[path]), 'SOURCE_EXTENT')
            extent = sources[path][start:end]
            source_records.append(dict(code=c, path=path, start=start, end=end,
                                       source_sha256=sha(sources[path]), extent_sha256=sha(extent),
                                       text=extent.decode('utf-8'), meaning='Reported source extent, not an IR-body witness'))
        pending.extend(literals)
    return dict(version=1, scope=SCOPE, census_gate_credit=False, process=process,
                roots=sorted(roots), functions=[records[c] for c in sorted(records)],
                source_extents=sorted(source_records, key=lambda r:r['code']))


def edge(c, targets, evidence, complete=True, phase='run'):
    return {'from': PREFIX+str(c), 'targets': [PREFIX+str(t) for t in sorted(targets)],
            'phase': phase, 'origin': 'observed' if complete else 'conservative',
            'resolution': 'complete' if complete else 'unresolved', 'evidence': evidence}


def make_delta(facts, base):
    ids = {n['id'] for n in base['nodes']}
    require(len(ids) == len(base['nodes']), 'BASE_NODE_UNIQUENESS')
    require(all(PREFIX+str(c) in ids for c in facts['roots']), 'BASE_ROOT_COVERAGE')
    nodes = []; edges = []
    for r in facts['functions']:
        c = r['code']; key = PREFIX+str(c)
        if key not in ids:
            nodes.append(dict(id=key, kind='function', disposition='implemented', required=True,
                              implementation='Recorded native build identity', evidence=f'resident-literals/code/{c}',
                              reason='Read-only function literal identity; native body dependencies and target implementation remain open.',
                              tests=['S0-LL15-b', 'S0-LL15-c']))
            edges.append(edge(c, [], f'resident-literals/body/{c}', False, 'compile'))
        if r['literal_codes']:
            edges.append(edge(c, r['literal_codes'], f'resident-literals/initial/{c}'))
    return dict(version=1, scope=SCOPE, census_gate_credit=False, nodes=nodes, edges=edges)


def apply(base, delta):
    ids = {n['id'] for n in base['nodes']}; evs = {e['evidence'] for e in base['edges']}
    require(not ids.intersection(n['id'] for n in delta['nodes']), 'NODE_COLLISION')
    require(not evs.intersection(e['evidence'] for e in delta['edges']), 'EDGE_COLLISION')
    return dict(base, nodes=base['nodes']+delta['nodes'], edges=base['edges']+delta['edges'],
                profile=base['profile']+'; '+SCOPE)


def check(facts, delta, graph, expected_facts, base):
    # Full record and edge sequence equality bounds both omissions and insertions,
    # including changes to earlier unresolved obligations or arbitrary metadata.
    require(facts == expected_facts, 'LITERAL_FACTS')
    expected = make_delta(expected_facts, base)
    require(delta == expected, 'LITERAL_DELTA')
    require(graph == apply(base, expected), 'LITERAL_GRAPH')


def summarize(facts, delta, graph):
    rows = {r['code']:r for r in facts['functions']}
    counts = Counter(t for c in facts['roots'] for t in rows[c]['literal_codes'])
    return dict(scope=SCOPE, census_gate_credit=False, roots=len(facts['roots']),
                readonly_targets=len(rows)-len(facts['roots']),
                direct_targets=[dict(code=c, description=rows[c]['descriptor']['description'], roots=n)
                                for c, n in sorted(counts.items())],
                literal_edges=sum(e['resolution']=='complete' for e in delta['edges']),
                added_nodes=len(delta['nodes']), new_body_obligations=sum(e['resolution']=='unresolved' for e in delta['edges']),
                graph_nodes=len(graph['nodes']), graph_edges=len(graph['edges']),
                existing_records_changed=0, source_ir_bodies_closed=0,
                computed_calls_changed=False, widening_edges_removed=0, callable_subtypes_proven=0)
