"""Close the remaining read-only loader body through its initial marker."""
from copy import deepcopy
from pathlib import Path
import hashlib
from payloads import read,save,require,rows,capture,before_functions,correspondences,source_key
from deferred import EXPANDER,MACRO_MARKER,collect,index,check_links
from bodies import extract,make,apply,with_initializers

HERE=Path(__file__).resolve().parent


def read_marker(row,functions,source):
    require(row['kind']=='deferred-marker-read','INITIAL_MARKER_READ')
    symbols={r['id']:r for r in row['symbol_description']['objects']}
    token=symbols[row['symbol_description']['root']['ref']]
    require(token==dict(id=row['symbol'],kind='symbol',name='LOAD-TIME-EVAL',package=None,setter_of=None),
            'INITIAL_MARKER_SYMBOL')
    nodes={r['id']:r for r in row['macro']['objects']};wrapper=nodes[row['macro']['root']['ref']]
    require(wrapper['kind']=='simple-vector' and wrapper['expanded'] and wrapper['length']==len(wrapper['elements'])==2
            and wrapper['elements'][0]=={'integer':MACRO_MARKER},'INITIAL_MARKER_TAG')
    fn=nodes[wrapper['elements'][1]['ref']]
    require(fn['kind']=='function' and fn['id']==fn['code'] and fn['id'] in functions,'INITIAL_MARKER_FUNCTION')
    native=functions[fn['id']];text=(source/'lib/nfcomp.lisp').read_bytes();start=text.index(EXPANDER);end=start+len(EXPANDER)
    require(source_key(native['source'])=='lib/nfcomp.lisp' and (native['source_start'],native['source_end'])==(start,end)
            and source_key(fn['description']['source'])=='lib/nfcomp.lisp' and fn['description']['position']==start,
            'INITIAL_MARKER_MACRO_SOURCE')
    return dict(symbol=token['id'],event=row['build_event'],read_event=row['sequence'],expander=fn['id'],span=[start,end],
                relation='OBSERVED_INITIAL_U1_LOAD_TIME_EVAL_MACRO',source_sha256=hashlib.sha256(text).hexdigest())


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    require(read(a.native/'summary.json')['status']=='PASS','INITIAL_MARKER_NATIVE')
    require(read(a.remaining)==[1824],'INITIAL_MARKER_REMAINING_POPULATION')
    fs,em,_,wrappers,_=capture(a.native/'registries.jsonl.gz',{'deferred-marker-read'})
    token=next(r for r in rows(a.native/'registries.jsonl.gz') if r['kind']=='deferred-marker-read')
    marker=read_marker(token,fs,a.source)
    before=before_functions(a.native/'build.jsonl.gz',em)
    deferred=collect(a.native/'build.jsonl.gz',fs,em,before,a.source,{},initial_markers=[marker])
    require(not deferred['unjoined'],'INITIAL_MARKER_MISSING_INITIALIZER')
    requested=next(r for r in read(a.evidence/'2026-09-14-resident-bodies-r1/bodies.json.gz')['bodies'] if r['code']==1824)
    asks=dict(bodies=[requested])
    matched,missing=correspondences(fs,em,wrappers,asks,before,data_dependencies=True,deferred=index(deferred))
    require(len(matched)==1 and not missing,'INITIAL_MARKER_BODY_MATCH')
    tests=[]
    no_marker=collect(a.native/'build.jsonl.gz',fs,em,before,a.source,{})
    without,_=correspondences(fs,em,wrappers,asks,before,data_dependencies=True,deferred=index(no_marker))
    require(not without,'INITIAL_MARKER_OMISSION_ESCAPED');tests.append(dict(name='missing-initial-marker',status='REJECTED'))
    def refuse(name,change,reason):
        bad=deepcopy(token);change(bad)
        try:read_marker(bad,fs,a.source)
        except ValueError as e:require(str(e)==reason,'INITIAL_MARKER_CONTROL_REASON '+name)
        else:raise ValueError('INITIAL_MARKER_CONTROL_ESCAPED '+name)
        tests.append(dict(name=name,status='REJECTED'))
    refuse('different-marker-symbol',lambda r:r.update(symbol=-1),'INITIAL_MARKER_SYMBOL')
    refuse('forged-macro-wrapper',lambda r:r['macro']['objects'][0]['elements'].__setitem__(0,{'integer':0}),'INITIAL_MARKER_TAG')
    refuse('wrong-macro-source',lambda r:r['macro']['objects'][1]['description'].update(position=0),'INITIAL_MARKER_MACRO_SOURCE')
    bad=deepcopy(fs);bad[marker['expander']]['source_end']+=1
    try:read_marker(token,bad,a.source)
    except ValueError as e:require(str(e)=='INITIAL_MARKER_MACRO_SOURCE','INITIAL_MARKER_NATIVE_SOURCE_CONTROL')
    else:raise ValueError('INITIAL_MARKER_NATIVE_SOURCE_ESCAPED')
    tests.append(dict(name='wrong-native-source-span',status='REJECTED'))
    snapshot=next(r['payload'] for r in rows(a.native/'build.jsonl.gz') if r['kind']=='snapshot')
    ops={r['id']:r['name'] for r in snapshot['operators']}
    families,calls=extract(a.native/'build.jsonl.gz',with_initializers(matched,deferred['placeholders']),ops)
    base=read(a.base);delta=make(base,matched,families,calls,deferred=deferred['placeholders'],namespace='initial-wrapper:')
    graph=apply(base,delta);check_links(graph,deferred['placeholders'],'initial-wrapper:')
    for name,value in [('marker.json',marker),('body-correspondence.json',matched),('deferred.json.gz',deferred),
                       ('controls.json',tests),('ir.json.gz',dict(functions=families,calls=calls)),
                       ('delta.json.gz',delta),('census.json.gz',graph),('remaining.json',[])]:save(a.output/name,value)
    from support import load_module
    errors=load_module('initial_marker_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'INITIAL_MARKER_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',remaining_readonly_bodies=0,body=1824,controls=len(tests),
        initializer_results_qualified=False,initializer_effects_qualified=False,caller_bounds_transferred=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','source','remaining','base','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
