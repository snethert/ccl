#!/usr/bin/env python3
import argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from backend import generate,replace,base
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'constants'))
p=HERE.parent/'constants/inherited.py'
spec=importlib.util.spec_from_file_location('accepted_harness',p)
harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def run(evidence,out):
 out.mkdir(parents=True,exist_ok=False);harness.generate=generate
 h=harness.prepare(out/'harness');shutil.copy(HERE/'probe.py',h/'probe.py')
 # The native implicit-error oracle previously classified only function type
 # errors. Classify the actual native TYPE-ERROR condition for list failures.
 p=h/'compile.lisp';text=p.read_text()
 text=replace(text,'(t "UNEXPECTED")','((and *implicit-error-suite* (typep c \'type-error)) "TYPE") (t "UNEXPECTED")')
 p.write_text(text)
 backend=generate();(out/'wasm32-backend.lisp').write_text(backend)
 controls=[]
 variants={'positive':backend,'old-refusal':base.generate(),
  'wrong-condition-class':replace(backend,'(else (i32.const 156))))))))','(else (i32.const 2076))))))))')}
 for name,source in variants.items():
  p=out/(name+'.lisp');p.write_text(source)
  command=[sys.executable,str(h/'probe.py'),str(evidence),str(out/name),str(p)]
  save(out/(name+'-command.json'),command)
  with (out/(name+'.log')).open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240)
  if name=='positive':
   if r.returncode:raise ValueError('positive failed: '+str(out/'positive.log'))
  else:
   log=(out/name/'execution.log').read_text()
   if r.returncode==0 or 'ap_catch-0: native/logical result' not in log:raise ValueError('mutant did not fail its execution oracle: '+name)
   controls.append({'name':name,'status':'REJECTED','diagnostic':'ap_catch-0: native/logical result'})
 save(out/'controls.json',controls)
 summary=json.loads((out/'positive/summary.json').read_text())
 save(out/'summary.json',{'status':'PASS','modules':summary['modules'],'comparisons':summary['comparisons'],'controls':controls,'scope':'APPLY non-list and dotted-tail Lisp TYPE-ERROR transfer; auxiliary LL19 prerequisite, not slot qualification.'})
 print(json.dumps(json.loads((out/'summary.json').read_text())))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
