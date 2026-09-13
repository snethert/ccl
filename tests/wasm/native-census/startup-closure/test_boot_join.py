"""Omission, insertion and false-promotion controls on the genuine boot slice."""
from copy import deepcopy
from boot_join import key
from check_boot import check, check_materialized


def run(base, delta, expected, graph):
    outcomes = []
    def reject(name, field, predicate, mutate, reason):
        damaged = dict(delta); damaged[field] = list(delta[field])
        index = next(i for i, r in enumerate(damaged[field]) if predicate(r))
        damaged[field][index] = deepcopy(damaged[field][index])
        mutate(damaged[field], index)
        try: check(damaged, expected)
        except ValueError as exc:
            if str(exc) != reason: raise ValueError(name + ': wrong refusal ' + str(exc))
        else: raise ValueError(name + ': escaped')
        outcomes.append({'name': name, 'status': 'REJECTED', 'reason': reason})
    def edge_case(name, label, change):
        reject(name, 'edges', lambda r: r['evidence'].startswith(label), change, 'EDGE_RECORDS')
    remove = lambda rows, i: rows.pop(i)
    edge_case('omit-boot-scenario-edge', 'boot/separate-process-witness', remove)
    edge_case('omit-cold-source-edge', 'boot/cold-origin/1', remove)
    edge_case('cross-process-callee-substitution', 'boot/function/', lambda a,i:a[i].update(targets=['identity:cold:code:1']))
    edge_case('invent-cross-process-edge', 'boot/event-coverage', lambda a,i:a.append({**a[i], 'targets':['identity:build:gap:boot-process']}))
    edge_case('duplicate-edge', 'boot/cold-origin/2', lambda a,i:a.append(deepcopy(a[i])))
    edge_case('wrong-load-module', 'boot/file/', lambda a,i:a[i].update(targets=[key('module','@execution')]))
    edge_case('wrong-reader-identity', 'boot/reader/', lambda a,i:a[i].update(targets=[key('object',1)]))
    edge_case('wrong-enclosing-effect', 'boot/enclosing/', lambda a,i:a[i].update(targets=[key('event',1)]))
    edge_case('omit-binding-old-value', 'boot/old/', remove)
    edge_case('substitute-binding-new-value', 'boot/new/', lambda a,i:a[i].update(targets=[key('object',1)]))
    edge_case('omit-initial-checkpoint', 'boot/initial-binding/', remove)
    edge_case('omit-final-checkpoint', 'boot/final-binding/', remove)
    edge_case('wrong-dispatch-table', 'boot/table/', lambda a,i:a[i].update(targets=[key('object',1)]))
    edge_case('promote-source-path-to-object-equality', 'boot/source-inventory-path/', lambda a,i:a[i].update(origin='observed'))
    edge_case('hide-closure-gap', 'boot/dependency-closure', remove)
    reject('omit-required-event', 'nodes', lambda r:r['id']==key('event',2), remove, 'NODE_RECORDS')
    reject('invent-implemented-function', 'nodes', lambda r:r['kind']=='function',
           lambda a,i:a.append({**a[i], 'id':key('object','invented')}), 'NODE_RECORDS')
    reject('change-function-metadata', 'nodes', lambda r:r['kind']=='function',
           lambda a,i:a[i].update(reason='invented source identity'), 'NODE_RECORDS')
    reject('promote-opaque-binding-value', 'nodes', lambda r:r['kind']=='store' and r['disposition']=='unresolved',
           lambda a,i:a[i].update(disposition='implemented',implementation='assumed callable'), 'NODE_RECORDS')
    reject('invent-initializer-return', 'initializers', lambda r:'call-enter' in r['completion_assertion'],
           lambda a,i:a[i].update(completion_assertion='Completed call and returned.'), 'INITIALIZER_RECORDS')
    reject('cyclic-event-order', 'initializers', lambda r:r['rank']==2,
           lambda a,i:a[i].update(prerequisites=[a[i]['node']]), 'INITIALIZER_RECORDS')
    reject('omit-event-prerequisite', 'initializers', lambda r:r['rank']==3,
           lambda a,i:a[i].update(prerequisites=[]), 'INITIALIZER_RECORDS')
    reject('duplicate-initializer', 'initializers', lambda r:True,
           lambda a,i:a.append(deepcopy(a[i])), 'INITIALIZER_RECORDS')
    reject('omit-unobserved-module', 'unobserved_modules', lambda r:True, remove, 'MODULE_RECORDS')
    reject('omit-cold-origin', 'cold_origins', lambda r:True, remove, 'COLD_ORIGIN_RECORDS')
    reject('invent-missing-source-range', 'cold_origins', lambda r:r['context'] is None,
           lambda a,i:a[i].update(context={'start':0,'end':1}), 'COLD_ORIGIN_RECORDS')
    reject('change-origin-fasl-offset', 'cold_origins', lambda r:True,
           lambda a,i:a[i].update(opcode_offset=0), 'COLD_ORIGIN_RECORDS')
    reject('conceal-active-handoff-frame', 'active_handoff', lambda r:True, remove, 'HANDOFF_RECORDS')
    # The graph assembler must not discharge an older run's missing witness,
    # change its seeds or turn this process into a file in the external trace.
    for name, field, mutate, reason in [
        ('promote-historical-boot-gap','nodes',lambda a:a.__setitem__(next(i for i,r in enumerate(a) if r['id']=='identity:build:gap:boot-process'),
          {**next(r for r in a if r['id']=='identity:build:gap:boot-process'),'disposition':'implemented','implementation':'assumed same run'}),'GRAPH_NODES'),
        ('remove-original-loader-seed','seeds',lambda a:a.pop(),'GRAPH_SEEDS'),
        ('promote-boot-module-to-external-trace','observed_modules',lambda a:a.append(key('module','@execution')),'GRAPH_OBSERVED_MODULES')]:
        damaged=dict(graph);damaged[field]=list(graph[field]);mutate(damaged[field])
        try:check_materialized(base,damaged,delta)
        except ValueError as exc:
            if str(exc)!=reason:raise ValueError(name+': wrong refusal '+str(exc))
        else:raise ValueError(name+': escaped')
        outcomes.append({'name':name,'status':'REJECTED','reason':reason})
    return {'status':'PASS','controls_rejected':len(outcomes),'controls':outcomes}
