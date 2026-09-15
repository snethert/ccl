"""Native compiler placeholders, real FASL loading and initializer edges."""
from copy import deepcopy
from pathlib import Path
import hashlib
from payloads import rows,read,save,require,before_functions,correspondences,literal_regions
from deferred import placeholder,consumers,index,marker,EXPANDER,check_links
from bodies import extract,with_initializers,make,apply


def check(output):
    side=list(rows(output/'registries.jsonl'));fs={r['id']:r for r in side if r['kind']=='function'}
    emissions={}
    for r in side:
        if r['kind']=='compiler-materialization':
            for f in r['functions']:
                if f['function'] is not None:emissions.setdefault(f['function'],[]).append(dict(afunc=f['afunc'],event=r['build_event']))
    before=before_functions(output/'build.jsonl',emissions)
    token=next(r for r in side if r['kind']=='deferred-marker-read')
    markers={token['symbol']:token};found=[];examples=[]
    for row in rows(output/'build.jsonl'):
        if row['kind']!='before-pass2':continue
        objects={n['id']:n for n in row['payload']['ir']['objects']};rs=[]
        for i,n in objects.items():
            if n['kind']!='cons':continue
            r=placeholder(i,objects,markers)
            if r:
                r.update(event=row['sequence'],compiler_records=[dict(function=r['function'],**e,before=before[e['afunc']])
                  for e in emissions[r['function']] if before[e['afunc']]['event']<e['event']<row['sequence']])
                require(r['compiler_records'],'DEFERRED_NATIVE_INITIALIZER');rs.append(r);examples.append((objects,i))
        owners=consumers(objects,{r['object'] for r in rs})
        for r in rs:r['owners']=owners[r['object']]
        found.extend(rs)
    loaded={r['name']:r['function'] for r in side if r['kind']=='deferred-loaded'}
    require(set(loaded)=={'READ-LEFT','CLASS-OBJECT','SHARED-LIST','CALLABLE-RESULT','NESTED-VALUE'},'DEFERRED_NATIVE_POPULATION')
    requested={'bodies':[dict(code=i,payload_sha256=hashlib.sha256(bytes.fromhex(fs[i]['payload_hex'])).hexdigest()) for i in loaded.values()]}
    matches,missing=correspondences(fs,emissions,set(),requested,before,data_dependencies=True,deferred=index(dict(placeholders=found)))
    good={m['bootstrap_code'] for m in matches}
    save(output/'analysis.json',dict(matches=matches,missing=missing,loaded=loaded,placeholders=found))
    require(good==set(loaded.values())-{loaded['CALLABLE-RESULT']} and missing==[loaded['CALLABLE-RESULT']],
            'DEFERRED_NATIVE_BODY_PARTITION')
    require(all(m['metadata_disposition']=='UNRESOLVED' for m in matches),'DEFERRED_NATIVE_METADATA')
    native_values=[r for r in side if r['kind']=='deferred-value']
    require(len(native_values)==6 and all(r['matches'] for r in native_values),'DEFERRED_NATIVE_VALUES')
    require((output/'reference.dx64fsl').read_bytes()==(output/'observed.dx64fsl').read_bytes(),'DEFERRED_NATIVE_FASL_DIFFERENCE')
    controls=[];objects,ident=examples[0]
    def refuses(name,change):
        mutated=deepcopy(objects);change(mutated)
        require(placeholder(ident,mutated,markers) is None,'DEFERRED_CONTROL_ESCAPED '+name)
        controls.append(dict(name=name,status='REJECTED'))
    refuses('same-spelling-different-marker',lambda x:x[ident].update(car={'ref':max(x)+1}))
    refuses('cyclic-placeholder',lambda x:x[ident].update(cdr={'ref':ident}))
    refuses('unexpanded-placeholder',lambda x:x[ident].update(expanded=False))
    call_ref=objects[objects[ident]['cdr']['ref']]['car']['ref']
    operator=objects[call_ref]['car']['ref'];argument_tail=objects[call_ref]['cdr']['ref']
    function=objects[argument_tail]['car']['ref']
    refuses('foreign-funcall',lambda x:x[operator].update(package='CCL-DEFERRED-PROBES'))
    refuses('extra-argument',lambda x:x[argument_tail].update(cdr={'ref':argument_tail}))
    refuses('symbol-instead-of-function',lambda x:x[function].update(kind='symbol'))
    refuses('different-function-prototype',lambda x:x[function].update(code=function+1))
    empty,_=correspondences(fs,emissions,set(),requested,before,data_dependencies=True,deferred={})
    require(loaded['READ-LEFT'] not in {r['bootstrap_code'] for r in empty},'DEFERRED_WITHOUT_WITNESS')
    controls.append(dict(name='missing-initializer-witness',status='REJECTED'))
    # The marker's actual macro is read independently; the recognizer checks
    # its exact native source span, not an arbitrary uninterned symbol's name.
    objects={r['id']:r for r in token['macro']['objects']};root=max(objects)+100000
    objects[root]=dict(id=root,kind='cons',car={'ref':token['symbol']},cdr={'ref':root+1},expanded=True)
    objects[root+1]=dict(id=root+1,kind='cons',car=token['macro']['root'],cdr={'atom':'nil'},expanded=True)
    objects[token['symbol']]=dict(id=token['symbol'],kind='symbol',name='LOAD-TIME-EVAL',package=None,setter_of=None)
    row=dict(sequence=token['build_event'],payload=dict(root={'ref':root},objects=list(objects.values())))
    source=(Path(__file__).resolve().parents[4]/'lib/nfcomp.lisp').read_bytes();start=source.index(EXPANDER)
    require(marker(row,fs,(start,start+len(EXPANDER))) is not None,'DEFERRED_REAL_MARKER')
    require(marker(row,fs,(start+1,start+len(EXPANDER))) is None,'DEFERRED_WRONG_MACRO_SOURCE')
    controls.append(dict(name='wrong-expander-source',status='REJECTED'))
    snapshot=next(r['payload'] for r in rows(output/'build.jsonl') if r['kind']=='snapshot')
    operators={r['id']:r['name'] for r in snapshot['operators']}
    families,calls=extract(output/'build.jsonl',with_initializers(matches,found),operators)
    base=dict(nodes=[{'id':f'identity:build:code:{i}'} for i in good],edges=[
        {'from':f'identity:build:code:{i}','targets':[],'resolution':'unresolved','evidence':f'binding-versions/body/{i}'} for i in good])
    delta=make(base,matches,families,calls,deferred=found);graph=apply(base,delta);check_links(graph,found)
    actual=[n for n in graph['nodes'] if n['id'].startswith('correlated-build:deferred:')]
    require(len(actual)==5,'DEFERRED_RECURSIVE_INITIALIZERS')
    use=next(i for i,e in enumerate(graph['edges']) if e['evidence'].startswith('correlated-build/deferred-use/'))
    body=next(i for i,e in enumerate(graph['edges']) if e['evidence'].startswith('correlated-build/deferred-body/'))
    for name,mutate in [
        ('omit-initializer-use',lambda g:g['edges'].pop(use)),
        ('omit-initializer-body',lambda g:g['edges'].pop(body)),
        ('extra-initializer-edge',lambda g:g['edges'].append(deepcopy(g['edges'][use]))),
        ('wrong-initializer-body',lambda g:g['edges'][body].update(targets=[])),
        ('claim-result-materialized',lambda g:next(n for n in g['nodes'] if n['id']==actual[0]['id']).update(disposition='implemented'))]:
        damaged=deepcopy(graph);mutate(damaged)
        try:check_links(damaged,found)
        except ValueError:controls.append(dict(name=name,status='REJECTED'))
        else:raise ValueError('DEFERRED_GRAPH_CONTROL_ESCAPED '+name)
    result=dict(status='PASS',native_cases=6,body_matches=len(good),callable_result_remains_open=True,
                placeholders=len(found),reachable_initializers=len(actual),controls=controls,fasl_bytes_unchanged=True)
    save(output/'deferred-initializers.json',found);save(output/'controls.json',result);return result


if __name__=='__main__':
    import sys
    print(check(Path(sys.argv[1])))
