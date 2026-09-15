"""Exact census integration bounds for observed methods and registries."""
from collections import Counter
import json
from payloads import require
import bodies

def registry_records(methods,registry,method_targets):
    nodes=[];edges=[]
    population={m['method']['id']:m for m in methods}
    require(len(population)==len(methods),'METHOD_GRAPH_REPEATED_METHOD')
    require({m['id']:m for r in registry for m in r['methods']}==
            {i:m['method'] for i,m in population.items()},'METHOD_GRAPH_REGISTRY_POPULATION')
    require(set(method_targets)==set(population),'METHOD_GRAPH_BODY_COVERAGE')
    for m in methods:
        ident='method-census:method:'+str(m['method']['id'])
        nodes.append(bodies.node(ident,'method-census/method/'+str(m['method']['id']),
            'Observed method identity; receiver, captured environment, data and target materialization remain obligations.',True))
        edges.append(bodies.edge(ident,[method_targets[m['method']['id']]],'method-census/method-body/'+str(m['method']['id']),'compile'))
    for r in registry:
        ident='method-census:gf:'+str(r['gf'])
        nodes.append(bodies.node(ident,'method-census/gf/'+str(r['gf']),
            'Observed generic-function registry. This union does not bound future ADD-METHOD, class mutation or cache state.',True))
        targets=['method-census:method:'+str(m['id']) for m in r['methods']]
        edges.append(bodies.edge(ident,targets,'method-census/gf-methods/'+str(r['gf']),'run',False))
    return nodes,edges


def cell_join(e,bindings):
    if e['evidence'].startswith(('correlated-build/binding-values/','method-census:build/binding-values/')):
        symbol=int(e['evidence'].rsplit('/',1)[1]);targets=bindings.get(symbol)
        if targets:
            require(e['resolution']=='unresolved' and not e['targets'],'METHOD_GRAPH_ORIGINAL_CELL')
            return dict(e,targets=sorted('method-census:gf:'+str(i) for i in targets))
    return e


def project(base,groups,methods,registry,method_targets,bindings):
    nodes,edges=registry_records(methods,registry,method_targets)
    nodes=[n for g in groups for n in g['nodes']]+nodes
    edges=[e for g in groups for e in g['edges']]+edges
    # Observation is not a startup seed. Keep the native population, letting
    # existing seeds and references determine necessity. Reachable unresolved
    # nodes still fail the unchanged checker, regardless of the required flag.
    return dict(base,nodes=base['nodes']+[dict(n,required=False) for n in nodes],
                edges=[cell_join(e,bindings) for e in base['edges']+edges])


def check_join(base,graph,groups,methods,registry,bindings):
    require({k:v for k,v in graph.items() if k not in ('nodes','edges')}==
            {k:v for k,v in base.items() if k not in ('nodes','edges')},'METHOD_GRAPH_BASE_METADATA')
    targets={m['method']['id']:'method-census:'+(
        m['witness']['record']['unit'] if m['witness']['kind']=='OBSERVED_METHOD_REPLACEMENT' else 'build')+
        ':code:'+str(m['prototype']) for m in methods}
    ns,es=registry_records(methods,registry,targets)
    expected={n['id']:dict(n,required=False) for g in groups for n in g['nodes']}
    require(len(expected)==sum(len(g['nodes']) for g in groups),'METHOD_GRAPH_GROUP_COLLISION')
    for n in ns:
        require(n['id'] not in expected,'METHOD_GRAPH_RECORD_COLLISION');expected[n['id']]=dict(n,required=False)
    require(graph['nodes'][:len(base['nodes'])]==base['nodes'],'METHOD_GRAPH_BASE_NODES')
    actual=graph['nodes'][len(base['nodes']):]
    require(len(actual)==len(expected) and {n['id']:n for n in actual}==expected,'METHOD_GRAPH_ADDED_NODES')
    require(not ({n['id'] for n in base['nodes']}&set(expected)),'METHOD_GRAPH_BASE_COLLISION')
    # Only explicitly same-execution cells may acquire these observed values.
    # Reload symbol/object numbers have no identity in the build execution.
    def expected_edge(e):
        prefix=next((p for p in ('correlated-build/binding-values/','method-census:build/binding-values/')
                     if e['evidence'].startswith(p)),None)
        if prefix:
            values=bindings.get(int(e['evidence'][len(prefix):]),set())
            if values:
                require(not e['targets'] and e['resolution']=='unresolved','METHOD_GRAPH_INPUT_CELL')
                return dict(e,targets=sorted('method-census:gf:'+str(i) for i in values))
        return e
    originals=graph['edges'][:len(base['edges'])]
    require(len(originals)==len(base['edges']) and all(a==expected_edge(b) for a,b in zip(originals,base['edges'])),
            'METHOD_GRAPH_BASE_EDGES')
    key=lambda e:json.dumps(e,sort_keys=True,separators=(',',':'))
    added=[e for g in groups for e in g['edges']]+es
    require(Counter(key(e) for e in graph['edges'][len(base['edges']):])==
            Counter(key(expected_edge(e)) for e in added),'METHOD_GRAPH_ADDED_EDGES')
    gfids={r['gf'] for r in registry}
    require(all(set(v)<=gfids for v in bindings.values()),'METHOD_GRAPH_BINDING_GF')
