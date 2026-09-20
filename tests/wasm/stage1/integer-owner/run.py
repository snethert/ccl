import argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from derive import HERE,ROOT,compiler,loader,owner,execute,replace
from corpus import SOURCES,cases

def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def compile(e,out):
 prior=HERE.parent/'integer-condition-review';sys.path.insert(0,str(prior))
 spec=importlib.util.spec_from_file_location('owner_compile',prior/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.SOURCES=SOURCES;m.cases=cases
 source=(prior/'compile.lisp').read_text()
 source=replace(source,'(result (compile-integer-call-form form name (append (mapcar #\'first cases) \'("gd_condition" "gd_condition_gf" "gd_condition_args"))))', '(result (let ((*b-allocation-retry* t)) (compile-integer-call-form form name (append (mapcar #\'first cases) \'("gd_condition" "gd_condition_gf" "gd_condition_args")))))')
 m.compile(e,out,compiler(),source)
 sys.path.pop(0)
def prepare(out):
 for n in ['integer-service.mjs','allocation-service.mjs','binary.mjs','stub.wat']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['numeric-capabilities.mjs','admission.mjs']:shutil.copy(HERE/n,out/n)
 (out/'loader.mjs').write_text(loader());(out/'collector-owner.mjs').write_text(owner());(out/'execute.mjs').write_text(execute())
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',out/'stub.wat','-o',out/'stub.wasm'],out/'stub.log')
def run(e,out):
 compile(e,out);qualify(e,out)
def qualify(e,out):
 prepare(out)
 for mode in ['eager','cold']:
  command(['/usr/local/bin/node',out/'execute.mjs',out,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm',out/(mode+'.json'),mode],out/(mode+'.log'))
 import pressure;forced=pressure.run(out,sys.modules[__name__])
 command(['/usr/local/bin/node',forced/'execute.mjs',forced,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm',forced/'execution.json','pressure'],forced/'execution.log')
 import controls;controls.run(e,out,sys.modules[__name__])
 a=json.loads((out/'eager.json').read_text());b=json.loads((out/'cold.json').read_text());assert a==b,'cold/eager observations'
 rows=a['rows'];summary=dict(status='PASS',modules=len(a['admission']),native_cases=len(cases()),comparisons=sum(r.get('cases',0) for r in rows),collections=sum(r.get('moves',0) for r in rows ),growths=sum(r.get('growths',0) for r in rows),assurances=sum(r.get('ensures',0) for r in rows),rejected_faults=len(json.loads((out/'controls.json').read_text())['rows']),loader_checks=len(json.loads((out/'eager-admission.json').read_text())['rows']),cold_identical=True,compiler_unchanged=True,gate_credit=False)
 forced_rows=json.loads((forced/'execution.json').read_text())['rows'];summary.update(forced_comparisons=sum(r.get('cases',0) for r in forced_rows),forced_collections=sum(r.get('moves',0) for r in forced_rows),forced_constructor_entries={str(k):sum(r.get('pressureCounts',{}).get(str(k),0) for r in forced_rows) for k in [1,2,3]})
 save(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
