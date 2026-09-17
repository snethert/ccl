#!/usr/bin/env python3
"""Native-derived repeated-keyword regression over the accepted constants corpus."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'constants';ROOT=HERE.parents[3]
sys.path.insert(0,str(BASE))
import compile as compiler_run
from backend import generate,replace
spec=importlib.util.spec_from_file_location('ll10_followup',BASE/'review-followup/run.py')
followup=importlib.util.module_from_spec(spec);spec.loader.exec_module(followup)
sha=followup.sha;save=followup.save;read=followup.read

def overlay(out):
    followup.overlay(out)
    cases=read(HERE/'cases.json')
    if not all(f.count('(')==f.count(')') for f in cases.values()):raise ValueError('case parentheses')
    p=out/'compile.lisp';s=p.read_text()
    forms='\n'.join('(cons "'+name+'" \''+form+')' for name,form in cases.items())
    s=replace(s,'(cons "tail_pool"',forms+'\n     (cons "tail_pool"')
    p.write_text(s)
    p=out/'execute_compiled.mjs';s=p.read_text().replace('66016','66064')
    s=replace(s,'keywords:{}','keywords:{x:620134,y:620166,z:620198,"allow-other-keys":620230}')
    s=replace(s,"symbols={condition_handlers:600006}","symbols={condition_handlers:600006,dup_a:601006,dup_ap:601038,dup_b:601070,dup_bp:601102}")
    s=replace(s,'store(610000,243);store(610004,243);set(104,610000);set(108,2);', '''for(let i=0;i<6;i++)store(610000+4*i,243);set(104,610000);set(108,6);
 for(const [i,name] of ['dup_a','dup_ap','dup_b','dup_bp'].entries()){
  const base=symbols[name]-6;store(base,1850);for(let j=1;j<8;j++)store(base+4*j,77825);store(base+28,4*(i+2));
 }''')
    s=replace(s,"if(focus==='slot-zero')", "if(focus.startsWith('keyword:')){const name=focus.slice(8);assert.deepEqual(describe(invoke(name),name),expected[name],'keyword-values '+name);}\n  else if(focus==='slot-zero')")
    s=replace(s,'assert.equal(pair[1],get(116));', "assert.deepEqual(Array.from({length:6},(_,i)=>load(610000+4*i)),Array(6).fill(243),'binding vector restored');assert.equal(pair[1],get(116));")
    p.write_text(s)
    return out

def run(evidence,out):
    out.mkdir(parents=True,exist_ok=False)
    save(out/'inputs.json',followup.inputs(evidence))
    harness=overlay(out/'harness');compiler_run.HERE=harness
    spec=importlib.util.spec_from_file_location('keywords_executor',harness/'execute_compiled.py')
    executor=importlib.util.module_from_spec(spec);spec.loader.exec_module(executor)
    backend=generate();(out/'wasm32-backend.lisp').write_text(backend)
    positive=out/'positive';compiler_run.run(evidence,positive,backend);executor.run(positive)
    # Native, not the target emitter, supplies every expected value and identity.
    expected=read(positive/'expected.json')
    def values(name):return expected[name]['roots']
    def integer(n):return {'kind':'integer','value':str(n)}
    nil={'kind':'singleton','value':'nil'};true={'kind':'singleton','value':'t'}
    assert values('aliases_supplied')==[integer(9),true,integer(2),nil]
    assert values('aliases_absent')==[integer(1),nil,integer(2),nil]
    assert values('aliases_repeated_actual')==values('aliases_supplied')
    # Retain the native probe answers separately for small independent review.
    save(out/'native-keyword-answers.json',{n:expected[n] for n in read(HERE/'cases.json')})
    mutants={
      'bind-every-alias':('(= index (position name names :test #\'eq))','t','aliases_supplied'),
      'bind-last-alias':("(position name names :test #'eq)","(position name names :test #'eq :from-end t)",'plain_then_alias'),
      'last-actual-wins':('(b-stage-read sp)\n              (b-stage-value var','"(i32.const 77825)"\n              (b-stage-value var','aliases_repeated_actual'),
    }
    controls=[]
    for name,(old,new,focus) in mutants.items():
        followup.node(positive,harness,'keyword:'+focus)
        dest=out/name;compiler_run.run(evidence,dest,replace(backend,old,new))
        for filename in ('materialized.json','expected.json','lazy-stub.wasm'):shutil.copy(positive/filename,dest/filename)
        diagnostic='keyword-values '+focus
        followup.node(dest,harness,'keyword:'+focus,diagnostic)
        controls.append({'name':name,'status':'REJECTED','case':focus,'diagnostic':diagnostic})
        save(out/'controls.json',controls)
    # The old validator must refuse the same source; this guards accidental test bypass.
    dest=out/'old-validator'
    old=replace(backend,'(unless (keywordp key) (refuse :b-source))','(unless (and (keywordp key) (not (member key keys))) (refuse :b-source))')
    try:compiler_run.run(evidence,dest,old)
    except RuntimeError:
        log=(dest/'compile.log').read_text()
        if 'POOL-COMPILING aliases_supplied' not in log or 'B-SOURCE' not in log:raise
    else:raise ValueError('original validator unexpectedly accepts duplicate names')
    controls.append({'name':'old-validator','status':'REJECTED','case':'aliases_supplied','diagnostic':'B-SOURCE'})
    save(out/'controls.json',controls)
    execution=read(positive/'execution.json')
    assert execution['status']=='PASS'
    save(out/'summary.json',{'status':'PASS','scope':'Repeated formal keyword aliases: first formal and first supplied actual win; later formals default. Auxiliary proposal, NOT_REVIEWED; no gate credit.', 'keyword_forms':len(read(HERE/'cases.json')),'keyword_comparisons':3*len(read(HERE/'cases.json')),'execution':{k:execution[k] for k in ('modules','native_comparisons')},'controls':len(controls)})
    print(json.dumps(read(out/'summary.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
