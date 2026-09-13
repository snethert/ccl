"""Semantic corruption controls over genuine emission facts and graph additions."""
from copy import deepcopy
from collections import Counter
from check_lowering import check
from lowering_join import check_facts, operand, SUBPRIM, make_delta, apply_delta
from identity_join import key


def run(base, delta, facts, reviewed, oracle, table, samples, base_hash,
        image_operators, kernel_sha256, validate, baseline_errors):
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
    verify = lambda: check(base, delta, facts, base_hash, image_operators, kernel_sha256)
    verify()
    for label, prefix in [('emitter', 'emitter/'), ('template', 'function-templates/'),
                          ('handler', 'handler-templates/'), ('operator', 'operator-codes/'),
                          ('same-slot', 'same-operator-slot/'),
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
    same = next(e for e in delta['edges'] if '/same-operator-slot/' in e['evidence'])
    mutate('same-slot-endpoint-substitution', same, 'from', 'operator:0', verify, 'DELTA_EDGE_RECORDS')
    mutate('slot-witness-omitted', delta, 'operator_slots', delta['operator_slots'][1:], verify, 'OPERATOR_SLOT_WITNESSES')
    witness = delta['operator_slots'][0]
    mutate('slot-kernel-witness-substitution', witness, 'kernel_sha256', '0' * 64, verify, 'OPERATOR_SLOT_WITNESSES')
    mutate('slot-image-code-witness-substitution', witness['image'], 'function', -1, verify, 'OPERATOR_SLOT_WITNESSES')
    image_slot = next(o for o in image_operators if o['id'] == facts['operators'][0]['record']['id'])
    produce = lambda: make_delta(base, facts, base_hash, image_operators, kernel_sha256)
    for field in ('name', 'flags', 'encoded', 'handler'):
        changed = image_slot[field] + 1 if type(image_slot[field]) is int else 'INVENTED'
        for label, action in [('checker', verify), ('producer', produce)]:
            mutate('slot-' + field + '-mismatch-' + label, image_slot, field, changed, action, 'OPERATOR_SLOT_EQUALITY')
    # A missing numeric slot must fail even if another row has its name/handler.
    for label, action in [('checker', verify), ('producer', produce)]:
        mutate('slot-id-mismatch-' + label, image_slot, 'id', -1, action, 'OPERATOR_SLOT_EQUALITY')
    check_inputs = lambda: check_facts(facts, reviewed, oracle, table)
    for label, field, target_field, reason in [('function', 'emitters', 'templates', 'FUNCTION_TEMPLATE_COVERAGE'),
                                              ('handler', 'handlers', 'templates', 'HANDLER_TEMPLATE_COVERAGE')]:
        row = facts[field][0]
        mutate(label + '-candidate-narrowed', row, target_field, row[target_field][1:], check_inputs, reason)
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
    # Force one decoded operand outside the same-kernel table. The controlled
    # facts/oracle change is synthetic; the unchanged generic census checker
    # must see exactly one additional reachable unresolved dependency.
    unknown = max(table) + 1
    changed = list(root['elements']); changed[SUBPRIM[sample['template']][0]] = {'integer': unknown}
    root['elements'] = changed
    if operand(sample) != unknown: raise AssertionError('unknown operand not decoded')
    call = facts['subprimitive_calls'][0]
    synthetic = {**facts, 'subprimitive_calls': [{**call, 'offset': unknown, 'name': None}] + facts['subprimitive_calls'][1:]}
    altered_oracle = Counter(oracle)
    del altered_oracle[call['function'], call['template'], call['offset']]
    altered_oracle[call['function'], call['template'], unknown] = call['count']
    check_facts(synthetic, reviewed, altered_oracle, table)
    unknown_delta = make_delta(base, synthetic, base_hash, image_operators, kernel_sha256)
    check(base, unknown_delta, synthetic, base_hash, image_operators, kernel_sha256)
    unknown_id = key('build', 'unknown-subprimitive', unknown)
    node = next(n for n in unknown_delta['nodes'] if n['id'] == unknown_id)
    if node['disposition'] != 'unresolved' or node['implementation'] is not None or node['required'] is not True:
        raise AssertionError('unknown dependency was promoted')
    expected_errors = Counter(baseline_errors); expected_errors['unimplemented reachable node ' + unknown_id] += 1
    actual_errors = Counter(validate(apply_delta(base, unknown_delta)))
    if actual_errors != expected_errors: raise AssertionError('unknown offset did not add exactly one census refusal')
    unknown_case = {'name': 'unknown-offset-remains-unresolved', 'status': 'PASS', 'offset': unknown,
                    'node': unknown_id, 'additional_unimplemented_nodes': 1,
                    'scope': 'Synthetic operand/facts mutation over the genuine census; no native execution.'}
    verify(); check_inputs()
    return {'status': 'PASS', 'controls': result, 'operand_layout_cases': positives, 'unknown_offset_case': unknown_case}
