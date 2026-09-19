#!/usr/bin/env python3
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];CONTROL=HERE.parent/'control'
sys.path.insert(0,str(CONTROL))
spec=importlib.util.spec_from_file_location('ll19_run',CONTROL/'run.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
from schema import build,check

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def run(evidence,out):
 out.mkdir(parents=True,exist_ok=False)
 accepted=evidence/'2026-09-19-stage1-control-r1';pins=read(accepted/'source-pins.json')
 for name,h in pins.items():assert sha(ROOT/name)==h,name
 compiler=base.generate();assert compiler==(accepted/'wasm32-backend.lisp').read_text()==(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
 h=base.prepare(out/'harness');shutil.copy(HERE/'probe.py',h/'decline_probe.py')
 p=h/'compile.lisp';s=p.read_text();s=(HERE/'native-boundary.lisp').read_text()+'\n'+s
 # Capture the fixture's existing abort/classification hook before each tested
 # function overrides it. The native hook body and signalling path stay real.
 anchor='(progn (setq values (multiple-value-list (apply (cdr (assoc name *call-functions* :test #\'equal)) (mapcar #\'decode args)))) (setq status "RETURN"))'
 assert s.count(anchor)==2
 s=s.replace(anchor,'(let ((*ll19-declined-boundary* *debugger-hook*)) '+anchor+')',1);p.write_text(s)
 p=h/'conditions.mjs';s=p.read_text()
 # This focused corpus signals non-function TYPE-ERROR; the shared fatal code
 # 5 otherwise has the inherited call-error oracle label DESIGNATOR.
 s=s.replace("status=code===2||", "status=code===5?'TYPE':code===2||")
 p.write_text(s)
 cmd=[sys.executable,str(h/'decline_probe.py'),str(evidence),str(out/'positive'),str(h/'wasm32-backend.lisp')];save(out/'command.json',cmd)
 with (out/'run.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
 execution=read(out/'positive/execution.json');assert execution['comparisons']==16 and execution['status']=='PASS'
 expected=[dict(version=1,stage='ordinary-error-service',function=name,kind='checked-runtime-error',code=5,transport='wasm-tag',recoverable=False) for name in ('d_decline','d_decline_many','d_no_hook','d_handler_then_hook')]
 assert execution['fatal_diagnostics']==expected*4,execution['fatal_diagnostics']
 old=read(ROOT/'doc/WASM/contracts/tcr.v1.json');new=build();assert new==read(ROOT/'doc/WASM/contracts/tcr.v2.json')
 save(out/'tcr.v2.json',new);controls=[]
 for name,edit in [('moved-offset',lambda x:x['fields'][-1].update(offset=252)),('reused-scratch-name',lambda x:next(f for f in x['fields'] if f['name']=='debugger_depth').update(name='scratch1')),('alias-collision',lambda x:x['compatibility']['aliases'].update(scratch0='debugger_depth'))]:
  bad=copy.deepcopy(new);edit(bad)
  try:check(old,bad)
  except AssertionError:controls.append(dict(name=name,status='REJECTED'))
  else:raise AssertionError(name)
 for name,edit in [('stage-relabel',lambda x:x[0].update(stage='bootstrap')),('lost-diagnostic',lambda x:x.pop()),('engine-trap',lambda x:x[0].update(transport='engine-trap'))]:
  bad=copy.deepcopy(execution['fatal_diagnostics']);edit(bad);assert bad!=expected*4;controls.append(dict(name=name,status='REJECTED'))
 save(out/'controls.json',controls);save(out/'summary.json',dict(status='PASS',modules=execution['modules'],native_cases=4,comparisons=16,ordinary_fatal_diagnostics=16,controls=len(controls),compiler_sha256=sha(accepted/'wasm32-backend.lisp'),native_boundary='U1 %break-message observed after the real hook returns; private image only.',native_R6='Reuse accepted exact compiler; no implementation change.'))
 for name,hsh in pins.items():assert sha(ROOT/name)==hsh,name
 print(json.dumps(read(out/'summary.json')))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
