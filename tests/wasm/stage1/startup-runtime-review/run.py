import argparse,importlib.util,json,shutil,sys
from pathlib import Path
from derive_unit import PARENT,service,compile_source,check
import classification
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(PARENT))
spec=importlib.util.spec_from_file_location('original_runtime_run',PARENT/'run.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
sha,read,save,command=old.sha,old.read,old.save,old.command

def run(e,out):
 out.mkdir(parents=True);stage=out/'driver';stage.mkdir()
 p=e/'2026-09-20-stage1-startup-runtime-r1'
 for n,h in read(p/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for n in ['statistics.mjs']:shutil.copy(PARENT/n,stage/n)
 (stage/'service.mjs').write_text(service());(stage/'compile.lisp').write_text(compile_source());(stage/'check.mjs').write_text(check());save(stage/'classification.json',classification.classify())
 # The owner derivation is unchanged; the condition image is a harness fixture.
 sys.path.insert(0,str(PARENT.parent/'startup-joined'))
 old.HERE=stage
 sys.modules['classify']=classification
 spec=importlib.util.spec_from_file_location('controls',PARENT/'controls.py');controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(controls)
 original_controls=controls.controls
 def joined_controls(x,cmd,save):
  original_controls(x,cmd,save)
  followup_controls(x,cmd,save)
 sys.modules['controls']=controls;controls.controls=joined_controls
 # Parent copies a fixed file list. Embed the tiny condition-image helper in
 # the derived harness so the unchanged fault copier carries it too.
 text=(stage/'check.mjs').read_text().replace("import {installConditions} from './conditions.mjs';",(HERE/'conditions.mjs').read_text().replace('export function','function'))
 (stage/'check.mjs').write_text(text)
 old.run(e,out/'execution')
 for n,h in read(p/'source-pins.json').items():assert sha(ROOT/n)==h,n

def followup_controls(out,command,save):
 rows=read(out/'controls.json')
 mutations=[('sign-pad','if(a.at(-1)>=0x80000000)a.push(0);','', 'exact five native values')]
 for name,clause in [('table','table!==descriptor||'),('end','end!==descriptor+2||'),('operation','op!==5||'),('second operand','b!==NIL||'),('publication','pub!==result||'),('header','||v.getUint32(descriptor-6,true)!==250')]:
  mutations.append(('admission-'+name.replace(' ','-'),clause,'','admission '+name))
 mutations.append(('raw-clock-error','if(!owner.statistics.timingValid){[NIL,NIL,1,0].forEach((w,i)=>v.setUint32(pub+4*i,w,true));return 0;}','', 'timing unavailable'))
 for name,a,b,why in mutations:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['check.mjs','owner.mjs','statistics.mjs','service.mjs','sha256.mjs','bytes.mjs','collector.wasm','adapter.wasm']:shutil.copy(out/n,d/n)
  shutil.copytree(out/'compiled',d/'compiled')
  s=(d/'service.mjs').read_text();assert s.count(a)==1,(name,a);(d/'service.mjs').write_text(s.replace(a,b))
  command(['/usr/local/bin/node',d/'check.mjs',d,d/'execution.json'],d/'rejected.log',why);rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',rows)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a=a.parse_args();run(a.evidence.resolve(),a.output.resolve())
