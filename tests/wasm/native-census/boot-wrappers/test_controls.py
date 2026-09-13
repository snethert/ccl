"""Controls on actual retained wrappers, their identities and graph joins."""
from copy import deepcopy
from join import validate_capture
from check import check, check_graph


def run(data,legacy,limit,base,patch,oracle,graph):
    rows=[]
    def expect(name,fn,reason):
        try:fn()
        except ValueError as exc:
            if str(exc)!=reason:raise ValueError(name+': wrong refusal '+str(exc))
        else:raise ValueError(name+': escaped')
        rows.append({'name':name,'status':'REJECTED','reason':reason})
    def capture(name,mutate,reason):
        altered=deepcopy(data);mutate(altered)
        expect(name,lambda:validate_capture(altered,legacy,limit),reason)
    capture('omit-wrapper',lambda d:d['wrappers'].pop(),'WRAPPER_COVERAGE')
    capture('duplicate-wrapper',lambda d:d['wrappers'].append(deepcopy(d['wrappers'][0])),'WRAPPER_COVERAGE')
    capture('omit-oracle',lambda d:d['oracle'].pop(),'ORACLE_COVERAGE')
    capture('change-dispatch-word',lambda d:d.update(dispatch_value=0),'DISPATCH_WORD')
    capture('change-wrapper-dispatch',lambda d:d['wrappers'][0].update(dispatch_value=0),'WRAPPER_DISPATCH')
    capture('change-payload-id',lambda d:d['wrappers'][0].update(payload=d['wrappers'][1]['payload']),'SLOT_ORACLE')
    capture('change-special-handler',lambda d:d['wrappers'][0].update(handler=None),'SLOT_ORACLE')
    capture('misclassify-special',lambda d:d['wrappers'][0].update(kind='macro-wrapper'),'SLOT_ORACLE')
    capture('omit-payload-object',lambda d:d['objects'].pop(0),'PAYLOAD_OBJECT')
    capture('alter-existing-symbol',lambda d:d['objects'][0].update(name='INVENTED'),'LEGACY_OBJECT_IDENTITY')
    capture('renumber-legacy-limit',lambda d:d.update(legacy_identity_limit=0),'LEGACY_IDENTITY_LIMIT')
    capture('alias-handler-table',lambda d:d.update(handler_table=d['objects'][0]['id']),'HANDLER_TABLE_ID')
    def graph_case(name,field,predicate,mutate,reason):
        altered=dict(patch);altered[field]=list(patch[field]);i=next(i for i,r in enumerate(altered[field]) if predicate(r))
        altered[field][i]=deepcopy(altered[field][i]);mutate(altered[field],i)
        expect(name,lambda:check(altered,oracle),reason)
    graph_case('omit-wrapper-replacement','replacements',lambda r:r['before']['kind']=='store',lambda a,i:a.pop(i),'REPLACEMENT_RECORDS')
    graph_case('invent-wrapper-content','replacements',lambda r:r['before']['kind']=='store',lambda a,i:a[i]['after'].update(reason='assumed contents'),'REPLACEMENT_RECORDS')
    graph_case('change-unrelated-gap-disposition','replacements',lambda r:r['before']['id']=='boot:gap:closure',lambda a,i:a[i]['after'].update(disposition='implemented'),'REPLACEMENT_RECORDS')
    graph_case('omit-macro-expander-edge','edges',lambda r:'/expander/' in r['evidence'],lambda a,i:a.pop(i),'EDGE_RECORDS')
    graph_case('wrong-expander-phase','edges',lambda r:'/expander/' in r['evidence'],lambda a,i:a[i].update(phase='run'),'EDGE_RECORDS')
    graph_case('substitute-special-handler','edges',lambda r:'/handler/' in r['evidence'],lambda a,i:a[i].update(targets=['boot:object:1']),'EDGE_RECORDS')
    graph_case('omit-trap-edge','edges',lambda r:'/dispatch/' in r['evidence'],lambda a,i:a.pop(i),'EDGE_RECORDS')
    graph_case('invent-extra-edge','edges',lambda r:True,lambda a,i:a.append({**a[i],'targets':['identity:build:gap:boot-process']}),'EDGE_RECORDS')
    graph_case('duplicate-edge','edges',lambda r:True,lambda a,i:a.append(deepcopy(a[i])),'EDGE_RECORDS')
    graph_case('alter-function-metadata','nodes',lambda r:r['kind']=='function',lambda a,i:a[i].update(reason='invented body identity'),'ADDED_NODE_RECORDS')
    graph_case('invent-extra-function','nodes',lambda r:r['kind']=='function',lambda a,i:a.append({**a[i],'id':'boot:object:invented'}),'ADDED_NODE_RECORDS')
    for name,field,mutate,reason in [
        ('drop-seed','seeds',lambda a:a.pop(),'GRAPH_SEEDS'),
        ('change-initializer-order','initializers',lambda a:a.reverse(),'GRAPH_INITIALIZERS'),
        ('promote-trace-module','observed_modules',lambda a:a.append('boot:module:@execution'),'GRAPH_OBSERVED_MODULES')]:
        altered=dict(graph);altered[field]=list(graph[field]);mutate(altered[field])
        expect(name,lambda:check_graph(base,altered,patch),reason)
    return {'status':'PASS','controls_rejected':len(rows),'controls':rows}
