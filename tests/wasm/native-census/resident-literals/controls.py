"""Insertion, substitution and false-closure controls on genuine joined records."""
import copy
import json
from join import apply, canonical, check, collect, require, sha


def run(inputs, facts, delta, graph, base):
    results = []

    def reject(name, reason, call):
        try:
            call()
        except ValueError as exc:
            require(str(exc) == reason, 'CONTROL_REASON '+name+': '+str(exc))
            results.append(dict(name=name, status='REJECTED', reason=reason))
        else:
            raise ValueError('CONTROL_ESCAPED '+name)

    for name, mutate in [
        ('omit-root', lambda f:f['roots'].pop()),
        ('invent-root', lambda f:f['roots'].append(999999999)),
        ('omit-reference', lambda f:next(r for r in f['functions'] if r['root'])['literal_codes'].clear()),
        ('name-only-target', lambda f:f['functions'][0].update(code=999999999)),
        ('invent-generic-function-subtype', lambda f:f['functions'][0].update(callable_subtype='GENERIC_FUNCTION')),
        ('promote-callee-bound', lambda f:f['functions'][0].update(exhaustive_callees=True)),
        ('promote-ir-body', lambda f:f['functions'][0].update(complete_ir_body=True)),
        ('promote-gate-credit', lambda f:f.update(census_gate_credit=True)),
        ('alter-source-extent', lambda f:f['source_extents'][0].update(text='(values)')),
    ]:
        damaged = copy.deepcopy(facts); mutate(damaged)
        reject(name, 'LITERAL_FACTS', lambda:check(damaged, delta, graph, facts, base))

    for name, mutate in [
        ('omit-edge', lambda d:d['edges'].pop()),
        ('duplicate-edge', lambda d:d['edges'].append(copy.deepcopy(d['edges'][-1]))),
        ('insert-cross-process-edge', lambda d:d['edges'].append(dict(d['edges'][-1], targets=['identity:cold:code:1']))),
        ('invent-implemented-node', lambda d:d['nodes'].append(dict(d['nodes'][0], id='identity:build:code:999999999'))),
        ('erase-new-body-obligation', lambda d:d['edges'].remove(next(e for e in d['edges'] if e['resolution']=='unresolved'))),
        ('complete-new-body-obligation', lambda d:next(e for e in d['edges'] if e['resolution']=='unresolved').update(resolution='complete')),
    ]:
        damaged = copy.deepcopy(delta); mutate(damaged)
        reject(name, 'LITERAL_DELTA', lambda:check(facts, damaged, graph, facts, base))

    damaged = dict(graph, edges=list(graph['edges']))
    i = next(i for i,e in enumerate(damaged['edges']) if e['evidence'].startswith('binding-versions/body/') and e['resolution']=='unresolved')
    damaged['edges'][i] = dict(damaged['edges'][i], resolution='complete')
    reject('complete-earlier-body-gap', 'LITERAL_GRAPH', lambda:check(facts, delta, damaged, facts, base))
    damaged = dict(graph, seeds=graph['seeds'][:-1])
    reject('alter-seed-set', 'LITERAL_GRAPH', lambda:check(facts, delta, damaged, facts, base))

    args = list(inputs)
    args[2] = list(args[2]); args[2][2] = args[2][2].replace(b'"code":2', b'"code":3')
    reject('substitute-readonly-prefix', 'ORIGINAL_READONLY_PREFIX', lambda:collect(*args))
    args = list(inputs); args[3] = copy.deepcopy(args[3]); args[3]['functions'][0]['code'] += 1
    reject('substitute-export-identity', 'READONLY_EXPORT_IDENTITY', lambda:collect(*args))
    args = list(inputs); args[3] = copy.deepcopy(args[3])
    target = facts['source_extents'][0]['code']
    next(r for r in args[3]['functions'] if r['code']==target)['source_end'] = -1
    reject('invalid-source-range', 'SOURCE_EXTENT', lambda:collect(*args))

    for name, reason, mutate in [
        ('foreign-process-root', 'INVENTORY_CONTEXT', lambda e:e.update(process=99)),
        ('wrong-function-root', 'FUNCTION_IDENTITY', lambda e:e['payload']['function'].update(root={'ref':-1})),
        ('unknown-literal-target', 'UNANCHORED_LITERAL_TARGET', lambda e:e['payload'].update(literal_functions=[999999999])),
        ('duplicate-literal-target', 'LITERAL_IDENTITY_SET', lambda e:e['payload']['literal_functions'].extend(e['payload']['literal_functions'])),
    ]:
        args = list(inputs); args[0] = copy.deepcopy(args[0]); args[1] = copy.deepcopy(args[1])
        row = next(r for r in args[0]['prototypes'] if r['code']==facts['roots'][0])
        index = next(i for i,line in enumerate(args[1]) if json.loads(line)['sequence']==row['first_descriptor']['event']['sequence'])
        event = json.loads(args[1][index])
        mutate(event)
        # A self-consistent alternate capture still must satisfy context, identity
        # and target availability; these controls exercise more than hash checks.
        args[1][index] = (canonical(event)+'\n').encode()
        row['first_descriptor']['event_sha256'] = sha(args[1][index])
        for key in row['first_descriptor']['event']:
            row['first_descriptor']['event'][key] = event[key]
        reject(name, reason, lambda:collect(*args))

    # The dynamic suffix belongs to the reproduction, not the original process.
    # Removing or replacing it cannot affect this join.
    args = list(inputs); args[2] = args[2][:inputs[4]['readonly_functions']+2] + [b'not JSON: deliberately ignored dynamic suffix\n']
    require(collect(*args) == facts, 'DYNAMIC_SUFFIX_USED')
    check(facts, delta, apply(base, delta), facts, base)
    return dict(controls_rejected=len(results), controls=results,
                positive_cases=['genuine-graph', 'dynamic-replay-suffix-ignored'])
