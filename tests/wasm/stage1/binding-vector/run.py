import os
import sys,importlib.util,shutil,json,subprocess,argparse
from pathlib import Path
from backend import generate,replace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('ll17_control_runner',HERE.parent/'control/run.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sys.path.insert(0,str(HERE))
def prepare(out):
 base.generate=generate;h=base.prepare(out);(h/'wasm32-backend.lisp').write_text(generate());shutil.copy(HERE/'probe.py',h/'binding_probe.py')
 p=h/'conditions.mjs';s=p.read_text()
 # All thirteen bootstrap symbols still fit initially; user symbols force two
 # successive growths while older bindings stay live.
 s=replace(s,'store(base+28,4*(i+1));','store(base+28,4*(i===0?31:i===1?63:i+1));')
 s=replace(s,"assert.deepEqual(Array.from({length:14},(_,i)=>load(610000+4*i)),[243,243,243,243,243,243,243,243,243,243,243,243,243,243],c.id+': binding vector restored');", "assert(Array.from({length:get(108)},(_,i)=>load(get(104)+4*i)).every(x=>x===243),c.id+': grown vector restored');assert.equal(get(0),37,c.id+': tcr_index namespace preserved');")
 s=replace(s,"w.on('message',x=>fs.writeFileSync(process.argv[3]+(x.progress?'.progress.json':''),JSON.stringify(x,null,2)+'\\n'));", "w.on('message',x=>{if(x.suspend){const d=new DataView(x.memory),get=o=>d.getUint32(x.tcr+o,true);assert.deepEqual([get(104),get(108),get(112),get(128),get(0),d.getUint32(get(104)+31*4,true)],x.state,'host sees suspended state');const sync=new Int32Array(x.sync);setTimeout(()=>{Atomics.store(sync,0,1);Atomics.notify(sync,0);},10);}else fs.writeFileSync(process.argv[3]+(x.progress?'.progress.json':''),JSON.stringify(x,null,2)+'\\n');});")
 s=replace(s,'let currentControlCase=null', 'let relocations=0,suspensions=0;const movedVectors=[];let currentControlCase=null')
 s=replace(s,"internalEntries++;inspect('internal '+m.name);", "internalEntries++;inspect('internal '+m.name);"+(HERE/'observer.mjs').read_text())
 s=replace(s,'currentControlCase=c;cleanupWitnesses=[];', 'currentControlCase=c;relocations=0;cleanupWitnesses=[];')
 s=replace(s,"parentPort.postMessage({status:'PASS',fatal_diagnostics:", "parentPort.postMessage({status:'PASS',suspensions,moved_vectors:movedVectors,fatal_diagnostics:")
 s=replace(s,'524294+i*16','524294+i*32')
 s=replace(s,'  set(104,610000);', '  for(const p of Object.values(keywords)){store(p-6,1850);for(let i=0;i<7;i++)store(p-2+4*i,NIL);store(p+2,p);store(p+14,8);store(p+22,0); }\n  set(104,610000);')
 s=replace(s,"   const savedArgs=",(HERE/'owner-input.mjs').read_text()+"   const savedArgs=")
 s=s.replace('[1,2,4,5,8,10,12,13,15,18,19,20].includes(code)', '[1,2,3,4,5,8,10,11,12,13,15,18,19,20].includes(code)').replace("status=code===2||", "status=code===3?'HEAP':code===11?'BINDING':code===2||")
 s=replace(s,"assert(Array.from({length:get(108)},(_,i)=>load(get(104)+4*i)).every(x=>x===243),c.id+': grown vector restored');",(HERE/'owner-check.mjs').read_text())
 p.write_text(s)
 p=h/'execute.mjs';s=p.read_text()
 anchor="   assert.throws(()=>invoke(fault==='partial-capacity'?'sd_sequential':'sd_bind',[44])"
 s=replace(s,anchor,(HERE/'inherited-growth.mjs').read_text()+anchor)
 s=replace(s,"assert.deepEqual(Array.from({length:14},(_,i)=>load(610000+4*i)),[243,243,243,243,243,243,243,243,243,243,243,243,243,243],'refused binding preserves TLB');", "if(!['index-limit','empty','partial-capacity'].includes(fault))assert.deepEqual(Array.from({length:14},(_,i)=>load(610000+4*i)),[243,243,243,243,243,243,243,243,243,243,243,243,243,243],'refused binding preserves TLB');")
 p.write_text(s)
 return h

def run(e,out,qualify=False):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 cmd=[sys.executable,str(h/'binding_probe.py'),str(e),str(out/'positive'),str(h/'wasm32-backend.lisp')]
 (out/'command.json').write_text(json.dumps(cmd));
 with (out/'run.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
 summary=json.loads((out/'positive/summary.json').read_text())
 assert summary['comparisons']==4*40 and summary['suspensions']==2
 assert [r['capacity'] for r in summary['moved_vectors']]==[14,32,64,32]*2
 from resources import run as resources
 resource=resources(h,out/'positive/compiled',out/'resources')
 controls=[]
 if qualify:
  from mutants import variants
  for name,source,focus in variants(generate(),replace):
   p=out/(name+'.lisp');p.write_text(source)
   environment=dict(os.environ)
   if focus:environment['LL17_CASES']=focus
   command=[sys.executable,str(h/'binding_probe.py'),str(e),str(out/name),str(p)]
   (out/(name+'-command.json')).write_text(json.dumps(dict(argv=command,LL17_CASES=focus)))
   with (out/(name+'.log')).open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=environment,timeout=180)
   if focus:
    assert r.returncode!=0,name+' escaped'
    failure=out/name/'execution.log';assert failure.exists(),name+' compiler did not reach execution'
   else:
    assert r.returncode==0,name+' positive execution failed'
    try:resources(h,out/name/'compiled',out/(name+'-resources'))
    except subprocess.CalledProcessError:pass
    else:raise AssertionError(name+' escaped resources')
    failure=out/(name+'-resources')/'execution.log'
   text=failure.read_text();assert 'AssertionError' in text,name+' unexpected failure'
   controls.append(dict(name=name,status='REJECTED',first_assertion=next(x.strip() for x in text.splitlines() if 'AssertionError' in x)))
 result=dict(status='PASS',modules=summary['modules'],native_cases=40,comparisons=summary['comparisons'],suspensions=summary['suspensions'],vector_evacuations=len(summary['moved_vectors']),resource_comparisons=resource['comparisons'],compiler_mutants=len(controls))
 (out/'controls.json').write_text(json.dumps(controls,indent=2)+'\n');(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.qualify)
