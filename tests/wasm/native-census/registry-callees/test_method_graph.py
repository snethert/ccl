"""Reject invented registry bounds, cross-run joins and missing method bodies."""
from copy import deepcopy
from payloads import require
from method_graph_check import check_join


def controls(base,graph,groups,methods,registry,bindings):
    result=[]
    def refuse(name,field,change,expected):
        damaged=dict(graph);damaged[field]=list(graph[field]);change(damaged[field])
        try:check_join(base,damaged,groups,methods,registry,bindings)
        except ValueError as e:
            require(str(e)==expected,'METHOD_GRAPH_CONTROL_REASON '+name+' '+str(e))
            result.append(dict(name=name,status='REJECTED'));return
        raise ValueError('METHOD_GRAPH_CONTROL_ESCAPED '+name)
    def edge_change(index,**fields):
        def mutate(rows):rows[index]=dict(rows[index],**fields)
        return mutate
    def edge_at(prefix):return next(i for i,e in enumerate(graph['edges']) if e['evidence'].startswith(prefix))
    method=edge_at('method-census/method-body/')
    union=edge_at('method-census/gf-methods/')
    original=next(i for i,e in enumerate(base['edges']) if e!=graph['edges'][i])
    refuse('omit-method-body','edges',lambda es:es.pop(method),'METHOD_GRAPH_ADDED_EDGES')
    refuse('duplicate-method-body','edges',lambda es:es.append(dict(es[method])),'METHOD_GRAPH_ADDED_EDGES')
    refuse('invent-complete-runtime-bound','edges',edge_change(union,resolution='complete'),'METHOD_GRAPH_ADDED_EDGES')
    refuse('empty-observed-registry','edges',edge_change(union,targets=[]),'METHOD_GRAPH_ADDED_EDGES')
    refuse('complete-function-cell-values','edges',edge_change(original,resolution='complete'),'METHOD_GRAPH_BASE_EDGES')
    refuse('invent-base-reference','edges',lambda es:es.insert(0,dict(es[method])),'METHOD_GRAPH_BASE_EDGES')
    wrong=graph['edges'][method]['targets'][0].replace(':build:',':describe:')
    refuse('method-body-wrong-execution','edges',edge_change(method,targets=[wrong]),'METHOD_GRAPH_ADDED_EDGES')
    reload=edge_at('method-census:describe/binding-values/')
    refuse('borrow-reload-cell-identity','edges',edge_change(reload,targets=graph['edges'][original]['targets']),
           'METHOD_GRAPH_ADDED_EDGES')
    first=len(base['nodes'])
    refuse('invent-implemented-function','nodes',lambda ns:ns.append(dict(ns[first],id='invented-function')),'METHOD_GRAPH_ADDED_NODES')
    refuse('omit-method-node','nodes',lambda ns:ns.pop(first),'METHOD_GRAPH_ADDED_NODES')
    refuse('claim-all-observed-methods-required','nodes',edge_change(first,required=True),'METHOD_GRAPH_ADDED_NODES')
    refuse('invent-materialization-description','nodes',edge_change(first,implementation='Invented implementation'),
           'METHOD_GRAPH_ADDED_NODES')
    refuse('alter-existing-obligation','nodes',edge_change(0,required=False,disposition='unsupported'),'METHOD_GRAPH_BASE_NODES')
    damaged=dict(graph,seeds=graph['seeds']+[graph['nodes'][first]['id']])
    try:check_join(base,damaged,groups,methods,registry,bindings)
    except ValueError as e:
        require(str(e)=='METHOD_GRAPH_BASE_METADATA','METHOD_GRAPH_SEED_CONTROL')
        result.append(dict(name='promote-observation-to-seed',status='REJECTED'))
    else:raise ValueError('METHOD_GRAPH_SEED_ESCAPED')
    return result
