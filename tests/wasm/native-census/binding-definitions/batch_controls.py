"""Regressions over exact input identities and the actual working graph."""
from copy import deepcopy
from definition_join import require,replay,check,patch,compiled,Graph
from classification import classify

def run(base,graph,delta,facts,histories,functions,witness,source_work):
    rows=[]
    def reject(name,fn,expected):
        try:fn()
        except ValueError as e:
            require(str(e)==expected,'CONTROL_REASON '+name+' '+str(e))
            rows.append(dict(name=name,status='REJECTED',reason=expected));return
        raise ValueError('CONTROL_ESCAPED '+name)
    def fact_mutation(name,mutate,reason='SELECTED_FACTS'):
        f=deepcopy(facts);mutate(f)
        reject(name,lambda:replay(witness,histories,functions,f),reason)
    fact_mutation('omit-compiled-name',lambda f:f['compiled'].pop())
    fact_mutation('same-name-different-symbol',lambda f:f['compiled'][0]['symbol'].update(id=-1))
    fact_mutation('different-native-body',lambda f:f['compiled'][0].update(function_id=-1))
    fact_mutation('different-code-version',lambda f:f['compiled'][0]['emitted'][0].update(code=-1))
    fact_mutation('different-source-position',lambda f:f['compiled'][0].update(source_position=-1))
    fact_mutation('omit-accessor-declaration',lambda f:f['declarations'].pop())
    fact_mutation('reader-promoted-to-writer',lambda f:f['declarations'][0]['entries'][0].update(role='WRITER'))
    fact_mutation('wrong-expansion-return',lambda f:f['declarations'][0].update(return_event=-1))
    fact_mutation('declarations-claimed-as-installations',lambda f:f.update(scope='INSTALLED_AND_BOUNDED'),'FACT_SCOPE')
    fact_mutation('hidden-incomplete-stream',lambda f:f.update(events=f['events']-1),'FACT_SCOPE')
    def delta_mutation(name,mutate):
        d=deepcopy(delta);mutate(d)
        reject(name,lambda:check(base,graph,d,facts),'EXACT_DECLARATION_PATCH')
    delta_mutation('compile-reference-made-runtime-bound',lambda d:d['edges'][0].update(phase='run'))
    delta_mutation('cross-execution-function',lambda d:d['edges'][0].update(targets=['seed-v2:function:1']))
    delta_mutation('extra-candidate-edge',lambda d:d['edges'].append(d['edges'][0]))
    delta_mutation('missing-class-construction-gap',lambda d:d['nodes'].pop())
    delta_mutation('class-construction-marked-implemented',lambda d:d['nodes'][0].update(disposition='implemented',implementation='fabricated'))
    delta_mutation('false-runtime-closure-credit',lambda d:d.update(original_runtime_obligations_closed=80))
    for name,field in [('omit-original-edge','edges'),('omit-original-node','nodes'),('erase-original-root','seeds')]:
        g=dict(graph);g[field]=g[field][1:]
        reject(name,lambda:check(base,g,delta,facts),'EXACT_GRAPH_PRESERVATION')
    g=dict(graph,edges=list(graph['edges']))
    i=next(i for i,e in enumerate(g['edges']) if e['evidence'].startswith('binding-versions/open/'))
    g['edges'][i]=dict(g['edges'][i],resolution='complete')
    reject('complete-runtime-value-with-compile-evidence',lambda:check(base,g,delta,facts),'EXACT_GRAPH_PRESERVATION')
    s=deepcopy(source_work);s['records'].pop()
    reject('omit-unjoined-source-case',lambda:classify(histories,facts,s),'REMAINING_SOURCE_WORK')
    s=deepcopy(source_work);s['records'][0]['descriptor']['id']=-1
    reject('source-name-used-as-object-identity',lambda:classify(histories,facts,s),'SOURCE_LOOKUP_DESCRIPTOR')
    return dict(status='PASS',controls_rejected=len(rows),controls=rows,
                scope='Reference-join and graph-preservation regressions, not independent LL15-c qualification.')
