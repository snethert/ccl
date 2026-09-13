"""Project native emission identities as an additive census fragment."""
from collections import Counter, defaultdict
import json

from exchange import ident
from identity_join import key

# Output slots precede arguments in vinsn-variable-parts. The pinned U1
# definitions have one label temporary except for JUMP-SUBPRIM.
SUBPRIM = {
    'CCL::JUMP-SUBPRIM': (0, 1), 'CCL::CALL-SUBPRIM': (0, 2),
    'CCL::CALL-SUBPRIM-NO-RETURN': (0, 2), 'CCL::CALL-SUBPRIM-1': (1, 4),
    'CCL::CALL-SUBPRIM-2': (1, 5), 'CCL::CALL-SUBPRIM-3': (1, 6)}
SCOPE = 'Observed native emission dependencies; live handler ancestry is not exact leaf dispatch or a static bound. Other template operands, imports, stores and Wasm dispositions remain unqualified.'


def operand(payload):
    position, length = SUBPRIM[payload['template']]
    graph = payload['parts']; objects = {r['id']: r for r in graph['objects']}
    if len(objects) != len(graph['objects']): raise ValueError('OPERAND_DUPLICATE_ID')
    root = objects.get(graph['root'].get('ref'), {})
    if (root.get('kind') != 'simple-vector' or root.get('expanded') is not True or
            root.get('length') != length or len(root.get('elements', [])) != length):
        raise ValueError('OPERAND_VECTOR')
    ref = root['elements'][position]
    if set(ref) != {'integer'} or type(ref['integer']) is not int:
        raise ValueError('OPERAND_CONSTANT')
    return ref['integer']


def capture(rows, reviewed, subprimitives):
    """Cross-check every emission against the reviewed join; retain compact facts."""
    expected = iter(reviewed['emissions']); last = 0; counts = Counter(); completed = False
    templates = {}; emitters = defaultdict(set); handlers = defaultdict(set); slots = defaultdict(set)
    calls = {}; samples = {}; raw_oracle = Counter(); snapshots = []
    functions = {r['function_id']: r for r in reviewed['functions']}
    for row in rows:
        seq = row['sequence']; kind = row['kind']
        if row['version'] != 2 or seq != last + 1 or completed: raise ValueError('EVENT_SEQUENCE')
        last = seq; counts[kind] += 1
        if kind == 'snapshot': snapshots.append(row['payload'])
        if kind == 'complete':
            expected_counts = {r['kind']: r['count'] for r in row['payload']['counts']}
            if expected_counts != {k: v for k, v in counts.items() if k != 'complete'} or row['payload']['events_before_complete'] != last - 1:
                raise ValueError('EVENT_COMPLETION')
            completed = True
        if kind != 'vinsn-emitted': continue
        p = row['payload']; frames = row['context']['handler_frames']; owner = row['function']
        # An independent, previously reviewed producer retained these fields.
        witness = next(expected, None)
        if witness != {'event': seq, 'function': owner, 'template': p['template'],
                       'template_id': p['template_id'], 'frames': frames}:
            raise ValueError('REVIEWED_EMISSION')
        if owner not in functions: raise ValueError('EMITTER_IDENTITY')
        tid = p['template_id']; meta = {'id': tid, 'name': p['template'], 'attributes': p['attributes']}
        if tid in templates and any(templates[tid][k] != v for k, v in meta.items()):
            raise ValueError('TEMPLATE_IDENTITY')
        if tid not in templates: templates[tid] = {**meta, 'count': 0, 'first_event': seq, 'last_event': seq}
        templates[tid]['count'] += 1; templates[tid]['last_event'] = seq
        emitters[owner].add(tid)
        for frame in frames:
            handlers[frame['code']].add(tid)
            for slot in frame['operators']: slots[slot].add(frame['code'])
        if p['template'] not in SUBPRIM: continue
        value = operand(p); group = owner, tid, value
        if group not in calls: calls[group] = {'function': owner, 'template': tid, 'offset': value, 'count': 0, 'first_event': seq, 'last_event': seq}
        calls[group]['count'] += 1; calls[group]['last_event'] = seq
        samples.setdefault(p['template'], row)
        # Literal-offset oracle, separate from operand() and its rule table.
        vector = next(r for r in p['parts']['objects'] if r['id'] == p['parts']['root']['ref'])
        index = 1 if p['template'] in ('CCL::CALL-SUBPRIM-1', 'CCL::CALL-SUBPRIM-2', 'CCL::CALL-SUBPRIM-3') else 0
        literal = vector['elements'][index]['integer']
        raw_oracle[owner, tid, literal] += 1
    if not completed or next(expected, None) is not None or counts != Counter(reviewed['counts']):
        raise ValueError('EMISSION_COVERAGE')
    if snapshots != reviewed['snapshots']: raise ValueError('SNAPSHOT_COVERAGE')
    operators = snapshots[0]['operators']
    if any(s['operators'] != operators or s['word_bits'] != 64 or s['backend'] != snapshots[0]['backend'] for s in snapshots):
        raise ValueError('NATIVE_TARGET_STATE')
    origins = {r['code']: r for r in reviewed['handler_origins']}
    if set(handlers) != set(origins) or any(r['origin'] == 'not-joined' for r in origins.values()):
        raise ValueError('HANDLER_ORIGINS')
    table = {r['offset']: r['name'] for r in subprimitives}
    if len(table) != len(subprimitives) or len(set(table.values())) != len(table): raise ValueError('SUBPRIMITIVE_TABLE')
    facts = {'version': 1, 'scope': SCOPE,
             'templates': [templates[i] for i in sorted(templates)],
             'emitters': [{'function': i, 'name': functions[i]['name'], 'templates': sorted(v)} for i, v in sorted(emitters.items())],
             'handlers': [{**origins[i], 'templates': sorted(v)} for i, v in sorted(handlers.items())],
             'operators': [{'record': operators[i], 'codes': sorted(v)} for i, v in sorted(slots.items())],
             'subprimitive_calls': [{**r, 'name': table.get(r['offset'])} for _, r in sorted(calls.items())],
             'subprimitive_rule_templates': sorted(SUBPRIM),
             'summary': {'events': last, 'emissions': counts['vinsn-emitted'], 'emitting_functions': len(emitters),
                         'template_identities': len(templates), 'template_names': len({r['name'] for r in templates.values()}),
                         'live_handler_codes': len(handlers), 'observed_operator_slots': len(slots),
                         'parameterized_subprimitive_calls': sum(r['count'] for r in calls.values()),
                         'subprimitive_targets': len({r['name'] for r in ({**r, 'name': table.get(r['offset'])} for r in calls.values()) if r['name'] is not None}),
                         'unmapped_subprimitive_calls': sum(r['count'] for r in calls.values() if r['offset'] not in table),
                         'rule_templates_seen': sorted(samples)}}
    check_facts(facts, reviewed, raw_oracle, table)
    return facts, samples, raw_oracle


def check_facts(facts, reviewed, raw_oracle, table):
    """Re-derive relation sets from the reviewed emissions, not projection output."""
    ft = defaultdict(set); ht = defaultdict(set); oc = defaultdict(set); tc = Counter(); names = {}; bounds = {}
    for r in reviewed['emissions']:
        tid = r['template_id']; ft[r['function']].add(tid); tc[tid] += 1; names[tid] = r['template']
        bounds.setdefault(tid, [r['event'], r['event']])[1] = r['event']
        for frame in r['frames']:
            ht[frame['code']].add(tid)
            for slot in frame['operators']: oc[slot].add(frame['code'])
    def relations(rows, id_field, targets, expected, reason):
        actual = {r[id_field]: set(r[targets]) for r in rows}
        if actual != expected or len(actual) != len(rows) or any(len(r[targets]) != len(set(r[targets])) for r in rows): raise ValueError(reason)
    relations(facts['emitters'], 'function', 'templates', ft, 'FUNCTION_TEMPLATE_COVERAGE')
    relations(facts['handlers'], 'code', 'templates', ht, 'HANDLER_TEMPLATE_COVERAGE')
    origins = {r['code']: r for r in reviewed['handler_origins']}
    names_by_function = {r['function_id']: r['name'] for r in reviewed['functions']}
    if any({k: v for k, v in r.items() if k != 'templates'} != origins[r['code']] for r in facts['handlers']):
        raise ValueError('HANDLER_ORIGIN_RECORD')
    if any(r['name'] != names_by_function[r['function']] for r in facts['emitters']): raise ValueError('FUNCTION_NAME_RECORD')
    operator_rows = {r['id']: r for r in reviewed['snapshots'][0]['operators']}
    if any(r['record'] != operator_rows.get(r['record']['id']) for r in facts['operators']): raise ValueError('OPERATOR_RECORD')
    actual = {r['record']['id']: set(r['codes']) for r in facts['operators']}
    if actual != oc or len(actual) != len(facts['operators']): raise ValueError('OPERATOR_CODE_COVERAGE')
    template_rows = {r['id']: r for r in facts['templates']}
    if len(template_rows) != len(facts['templates']) or set(template_rows) != set(tc): raise ValueError('TEMPLATE_COVERAGE')
    for tid, r in template_rows.items():
        if (r['name'], r['count'], r['first_event'], r['last_event']) != (names[tid], tc[tid], *bounds[tid]): raise ValueError('TEMPLATE_COUNTS')
    rows = facts['subprimitive_calls']; counts = {(r['function'], r['template'], r['offset']): r['count'] for r in rows}
    if counts != raw_oracle or len(counts) != len(rows) or any(r['name'] != table.get(r['offset']) for r in rows):
        raise ValueError('SUBPRIMITIVE_OPERAND_JOIN')


def node_record(i, kind, implementation, evidence, reason=''):
    return {'id': i, 'kind': kind, 'disposition': 'implemented', 'required': True,
            'implementation': implementation, 'evidence': evidence,
            'tests': ['S0-LL15-b', 'S0-LL15-c'], 'reason': reason}


def make_delta(base, facts, base_sha256):
    present = {r['id']: r for r in base['nodes']}; nodes = {}; edges = []
    def node(record):
        i = record['id']
        if i not in present: nodes[i] = record
        return i
    def edge(source, targets, evidence, origin='observed'):
        edges.append({'from': source, 'targets': sorted(set(targets)), 'phase': 'compile',
                      'origin': origin, 'resolution': 'complete', 'evidence': 'emission:build/' + evidence})
    surface = key('build', 'module', '@execution')
    for row in facts['templates']:
        node(node_record(key('build', 'template', row['id']), 'vinsn', row['name'], 'build/template/' + str(row['id']),
                         'Observed native template identity; attributes ' + str(row['attributes']) + '. Static emission and Wasm lowering remain unqualified.'))
    for row in facts['emitters']:
        i = node(node_record(key('build', 'afunc', row['function']), 'function', 'Recorded front-end function: ' + row['name'],
                             'build/emitter/' + str(row['function']), 'Emission identity only; complete call dependencies remain unqualified.'))
        edge(surface, [i], 'emitter/' + str(row['function']))
        edge(i, [key('build', 'template', t) for t in row['templates']], 'function-templates/' + str(row['function']))
    for row in facts['handlers']:
        i = node(node_record(key('build', 'code', row['code']), 'function', 'Recorded native handler code; origin ' + row['origin'],
                             'build/handler/' + str(row['code']), 'Live frame membership, not exact leaf dispatch.'))
        edge(i, [key('build', 'template', t) for t in row['templates']], 'handler-templates/' + str(row['code']))
    for row in facts['operators']:
        op = row['record']; i = node(node_record(key('build', 'operator', op['id']), 'operator', 'Evaluated native slot ' + str(op['id']),
                         'build/operator/' + str(op['id']), json.dumps(op, sort_keys=True, separators=(',', ':'))))
        edge(surface, [i], 'operator/' + str(op['id']))
        edge(i, [key('build', 'code', code) for code in row['codes']], 'operator-codes/' + str(op['id']))
    groups = defaultdict(set)
    for row in facts['subprimitive_calls']:
        if row['name'] is None:
            i = key('build', 'unknown-subprimitive', row['offset'])
            n = node_record(i, 'subprimitive', None, 'build/subprimitive-offset/' + str(row['offset']), 'Recorded operand has no entry in the same-kernel table.')
            n['disposition'] = 'unresolved'; node(n)
        else:
            i = ident('subprimitive', row['name'])
            if i not in present or present[i]['implementation'] != 'native table offset ' + str(row['offset']):
                raise ValueError('BASE_SUBPRIMITIVE_TABLE')
        groups[row['function']].add(i)
    for owner, targets in sorted(groups.items()):
        edge(key('build', 'afunc', owner), targets, 'subprimitive-targets/' + str(owner))
    return {'version': 1, 'base_sha256': base_sha256, 'scope': SCOPE,
            'nodes': [nodes[i] for i in sorted(nodes)], 'edges': edges}


def apply_delta(base, delta):
    result = dict(base)
    result['nodes'] = base['nodes'] + delta['nodes']; result['edges'] = base['edges'] + delta['edges']
    result['profile'] = base['profile'] + '; observed native emission joins (static coverage still unqualified)'
    return result
