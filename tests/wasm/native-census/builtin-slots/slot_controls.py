"""Corrupt actual operands, table entries and the integrated graph."""
from copy import deepcopy
from slots import require,check,facts,native_routes


def run(base,graph,patch,f,calls,functions,routes,obligations,samples,sources):
    results=[]
    def reject(name,fn,reason):
        try: fn()
        except ValueError as e:
            require(str(e)==reason, 'CONTROL_REASON '+name+' '+str(e))
            results.append(dict(name=name,status='REJECTED',reason=reason));return
        raise ValueError('CONTROL_ESCAPED '+name)
    def verify(g=graph,d=patch,value=f):
        check(base,g,d,value,calls,functions,routes,obligations)
    for name,change in [
        ('omit-slot',lambda x:x['slots'].pop()),
        ('omit-call-site',lambda x:x['slots'][0]['call_sites'].pop()),
        ('same-count-call-substitution',lambda x:x['slots'][0]['call_sites'][0]['call'].update(site_id=-1)),
        ('invent-function-cell-identity',lambda x:x['slots'][0].update(callable_identity='OBSERVED')),
        ('native-source-claimed-as-target-lowering',lambda x:x['slots'][0].update(target_lowering='QUALIFIED')),
        ('erase-computed-population',lambda x:x['open_computed_evidence'].pop()),
        ('hide-original-builtin-gaps',lambda x:x.update(original_unresolved_call_edges=1562)),
    ]:
        x=deepcopy(f);change(x)
        reject(name,lambda:verify(value=x),'EXACT_SLOT_FACTS')
    for name,change in [
        ('operand-slot-promoted-to-function',lambda x:x['nodes'][0].update(kind='function')),
        ('invent-target-implementation',lambda x:x['nodes'][0].update(disposition='implemented',implementation='native bytes')),
        ('change-slot-description',lambda x:x['nodes'][0].update(reason='fabricated')),
        ('close-shared-lowering-gap',lambda x:x['edges'][0].update(resolution='complete')),
        ('cross-execution-slot-target',lambda x:x['edges'][0].update(targets=['seed-v2:function:1'])),
        ('omit-site-replacement',lambda x:x['replacements'].pop()),
        ('change-site-phase',lambda x:x['replacements'][0].update(phase='compile')),
        ('duplicate-site-replacement',lambda x:x['replacements'].append(x['replacements'][0])),
    ]:
        x=deepcopy(patch);change(x)
        reject(name,lambda:verify(d=x),'EXACT_SLOT_PATCH')
    for name,field in [('omit-original-node','nodes'),('erase-original-root','seeds'),('omit-original-edge','edges')]:
        x=dict(graph);x[field]=x[field][1:]
        reject(name,lambda:verify(g=x),'EXACT_SLOT_GRAPH')
    x=dict(graph,nodes=graph['nodes']+[graph['nodes'][0]])
    reject('insert-node',lambda:verify(g=x),'EXACT_SLOT_GRAPH')
    x=dict(graph,edges=list(graph['edges']))
    i=next(i for i,e in enumerate(x['edges']) if e['evidence'].startswith('binding-versions/open/'))
    x['edges'][i]=dict(x['edges'][i],resolution='complete')
    reject('conceal-binding-gap',lambda:verify(g=x),'EXACT_SLOT_GRAPH')
    x=dict(graph,edges=graph['edges']+[dict(graph['edges'][0],targets=[f['slots'][0]['node']])])
    reject('insert-widening-edge',lambda:verify(g=x),'EXACT_SLOT_GRAPH')
    x=dict(graph,initializers=graph['initializers'][1:])
    reject('omit-initializer',lambda:verify(g=x),'EXACT_SLOT_GRAPH')
    x=deepcopy(samples);key=next(iter(x));x[key]['builtins']['10'],x[key]['builtins']['11']=x[key]['builtins']['11'],x[key]['builtins']['10']
    reject('snapshot-slot-substitution',lambda:native_routes(x,sources),'SNAPSHOT_TABLE_AGREEMENT')
    x=deepcopy(samples)
    for s in x.values():s['builtins']['10'],s['builtins']['11']=s['builtins']['11'],s['builtins']['10']
    reject('consistent-wrong-slot-order',lambda:native_routes(x,sources),'U1_BUILTIN_ORDER')
    x=deepcopy(samples)
    for s in x.values():del s['builtins']['0']
    reject('missing-unused-vector-slot',lambda:native_routes(x,sources),'BUILTIN_SLOT_COVERAGE')
    x=dict(sources);p='compiler/X86/X8664/x8664-arch.lisp'
    x[p]=x[p].replace(b':primitive->subprims `(((0 . 23)',b':primitive->subprims `(((0 . 22)')
    reject('native-range-off-by-one',lambda:native_routes(samples,x),'U1_PRIMITIVE_RANGE')
    x=dict(sources);p='lisp-kernel/x86-spentry64.s';x[p]=x[p].replace(b'_spentry(builtin_length)',b'_spentry(hidden_length)')
    reject('missing-native-source-entry',lambda:native_routes(samples,x),'U1_SUBPRIMITIVE_BODY')
    x=deepcopy(obligations);x['slots'][0]['status']='IMPLEMENTED'
    reject('worklist-as-implementation',lambda:facts(calls,functions,base,routes,x),'OBLIGATION_QUALIFICATION')
    x=deepcopy(obligations);x['slots'].pop()
    reject('omit-target-obligation',lambda:facts(calls,functions,base,routes,x),'OBLIGATION_SLOT_SET')
    i=next(i for i,c in enumerate(calls) if c['dependency']['category']=='builtin')
    x=list(calls);x[i]=deepcopy(x[i]);x[i]['dependency']['builtin_index']=10
    reject('wrong-IR-slot-with-original-name',lambda:facts(x,functions,base,routes,obligations),'CALL_SLOT_NAME')
    x=list(calls);x[i]=deepcopy(x[i]);x[i]['event']=-1
    reject('wrong-compiler-event',lambda:facts(x,functions,base,routes,obligations),'CALL_CONTEXT')
    x=list(calls);x.pop(i)
    reject('missing-original-call',lambda:facts(x,functions,base,routes,obligations),'CALL_EDGE_COVERAGE')
    return dict(status='PASS',controls_rejected=len(results),controls=results,
                scope='Slot/worklist and graph integration controls; no independent LL15-c qualification.')
