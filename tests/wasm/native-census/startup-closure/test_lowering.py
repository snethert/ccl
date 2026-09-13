"""Semantic corruption controls over genuine emission facts and graph additions."""
from copy import deepcopy
from check_lowering import check
from lowering_join import check_facts, operand, SUBPRIM


def run(base, delta, facts, reviewed, oracle, table, samples, base_hash):
    result = []
    def reject(name, function, reason):
        try: function()
        except ValueError as exc:
            if not str(exc).startswith(reason): raise AssertionError((name, str(exc), reason))
            result.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise AssertionError(name + ' escaped')
    def mutate(name, obj, field, value, function, reason):
        old = obj[field]; obj[field] = value
        try: reject(name, function, reason)
        finally: obj[field] = old
    verify = lambda: check(base, delta, facts, base_hash)
    verify()
    for label, prefix in [('emitter', 'emitter/'), ('template', 'function-templates/'),
                          ('handler', 'handler-templates/'), ('operator', 'operator-codes/'),
                          ('subprimitive', 'subprimitive-targets/')]:
        e = next(e for e in delta['edges'] if e['evidence'].startswith('emission:build/' + prefix))
        mutate(label + '-edge-omitted', delta, 'edges', [r for r in delta['edges'] if r is not e], verify, 'DELTA_EDGE_RECORDS')
    e = delta['edges'][0]
    mutate('cross-process-edge', e, 'from', e['from'].replace(':build:', ':cold:'), verify, 'DELTA_EDGE_RECORDS')
    mutate('surplus-edge', delta, 'edges', delta['edges'] + [e], verify, 'DELTA_EDGE_RECORDS')
    n = delta['nodes'][0]
    mutate('node-omitted', delta, 'nodes', delta['nodes'][1:], verify, 'DELTA_NODE_RECORDS')
    mutate('node-metadata-substitution', n, 'implementation', 'Invented implementation', verify, 'DELTA_NODE_RECORDS')
    mutate('node-surplus', delta, 'nodes', delta['nodes'] + [{**n, 'id': n['id'] + '-invented'}], verify, 'DELTA_NODE_RECORDS')
    mutate('wrong-base', delta, 'base_sha256', '0' * 64, verify, 'DELTA_BASE_SCOPE')
    check_inputs = lambda: check_facts(facts, reviewed, oracle, table)
    for label, field, key, reason in [('function', 'emitters', 'templates', 'FUNCTION_TEMPLATE_COVERAGE'),
                                     ('handler', 'handlers', 'templates', 'HANDLER_TEMPLATE_COVERAGE')]:
        row = facts[field][0]
        mutate(label + '-candidate-narrowed', row, key, row[key][1:], check_inputs, reason)
    row = facts['subprimitive_calls'][0]
    mutate('valid-but-wrong-subprimitive', row, 'name', next(v for v in table.values() if v != row['name']), check_inputs, 'SUBPRIMITIVE_OPERAND_JOIN')
    t = facts['templates'][0]
    mutate('emission-count-changed', t, 'count', t['count'] + 1, check_inputs, 'TEMPLATE_COUNTS')
    sample = deepcopy(next(iter(samples.values()))['payload'])
    root = next(r for r in sample['parts']['objects'] if r['id'] == sample['parts']['root']['ref'])
    mutate('truncated-operand-vector', root, 'length', 0, lambda: operand(sample), 'OPERAND_VECTOR')
    index = SUBPRIM[sample['template']][0]
    replacement = list(root['elements']); replacement[index] = {'integer': True}
    mutate('boolean-as-subprimitive-offset', root, 'elements', replacement, lambda: operand(sample), 'OPERAND_CONSTANT')
    # Distinct literal vectors exercise the output-before-argument convention,
    # including families that this native workload may never select.
    positives = []
    for name, index, size in [('CCL::JUMP-SUBPRIM', 0, 1), ('CCL::CALL-SUBPRIM', 0, 2),
                              ('CCL::CALL-SUBPRIM-NO-RETURN', 0, 2), ('CCL::CALL-SUBPRIM-1', 1, 4),
                              ('CCL::CALL-SUBPRIM-2', 1, 5), ('CCL::CALL-SUBPRIM-3', 1, 6)]:
        elements = [{'ref': 9}] * size; elements[index] = {'integer': 86016}
        p = {'template': name, 'parts': {'root': {'ref': 1}, 'objects': [{'id': 1, 'kind': 'simple-vector',
             'expanded': True, 'length': size, 'elements': elements}]}}
        if operand(p) != 86016: raise AssertionError('wrong literal operand slot: ' + name)
        positives.append({'name': name, 'status': 'PASS', 'scope': 'Synthetic operand-layout control, not native execution.'})
    verify(); check_inputs()
    return {'status': 'PASS', 'controls': result, 'operand_layout_cases': positives}
