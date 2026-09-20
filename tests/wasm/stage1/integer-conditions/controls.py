"""Executed condition and inline-route controls over generated modules."""
import hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def execute(e,out,driver,harness=None):
 for n in ['collector-owner.mjs','binary.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['service.mjs','execute.mjs']:shutil.copy(HERE/n,out/n)
 if harness is not None:(out/'execute.mjs').write_text(harness)
 driver.command(['/usr/local/bin/node',out/'execute.mjs',out,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm',out/'execution.json'],out/'execution.log')
def run(e,out,driver):
 execute(e,out,driver);rows=[];code=driver.generate()
 faults=[
 ('skip-type-signal','(i32.eqz (call $integer_operand ~a))','(i32.and (i32.const 0) (i32.eqz (call $integer_operand ~a)))','e_type_left'),
 ('wrong-condition-mask','(then (i32.const 196636))','(then (i32.const 28))','e_collect'),
 ('missing-condition-operands','(i32.eq (local.get $mask) (i32.const 196636))','(i32.eq (local.get $mask) (i32.const 196640))','e_collect'),
 ('wrong-expected-type',"((< op 3) 'number)","((< op 3) 'integer)",'e_type_left'),
 ('lost-condition-root','(i32.store offset=24 (local.get $frame) (local.get $condition))','(i32.store offset=24 (local.get $frame) (i32.const 77825))','e_collect'),
 ]
 # Every admitted operation has an independent execution assertion that it
 # takes the inline path. Mutate each separately, not one all-slow control.
 for op,name in enumerate(['add','sub','mul','ash','length','truncate']):faults.append(('slow-'+name,'(block $slow\n','(block $slow\n (br_if $slow (i32.eq (local.get $op) (i32.const '+str(op)+')))\n','inline n_'+name))
 for name,old,new,why in faults:
  assert code.count(old)==(2 if name=='lost-condition-root' else 1),(name,code.count(old));path=out/name;driver.compile(e,path,code.replace(old,new))
  try:execute(e,path,driver)
  except subprocess.CalledProcessError:
   text=(path/'execution.log').read_text();assert why in text,(name,why,text[-1600:]);rows.append(dict(name=name,oracle=why,status='REJECTED'))
  else:raise AssertionError('escaped '+name)
 for name,old,new,why in [('wrong-service-pin',"a56d7f7ff3d5472d9a72f28ea93bc00f521d52a45b15f9b47b5cda4a29c58f59",'0'*64,'retained integer service pin'),('nil-fill-as-zero',"if(v===NIL)return 'NIL';","if(v===NIL)return '0';",'e_short')]:
  s=(HERE/'execute.mjs').read_text();assert s.count(old)==1;path=out/name;path.mkdir();shutil.copytree(out/'compiled',path/'compiled');shutil.copy(out/'native.json',path/'native.json')
  try:execute(e,path,driver,s.replace(old,new))
  except subprocess.CalledProcessError:
   text=(path/'execution.log').read_text();assert why in text,(name,text[-1600:]);rows.append(dict(name=name,oracle=why,status='REJECTED'))
  else:raise AssertionError('escaped '+name)
 # Regenerate the reviewed default API corpus with this proposal. Its baseline
 # generator is bypassed by the explicit compiler argument.
 spec=importlib.util.spec_from_file_location('numeric_default',HERE.parent/'generic-dispatch/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.run(e,out/'default',backend=code)
 same=[]
 for f in sorted((e/'2026-09-19-stage1-generic-dispatch-r1/positive').glob('*')):
  if f.suffix in ['.wat','.wasm']:assert f.read_bytes()==(out/'default/compiled'/f.name).read_bytes(),f.name;same.append(f.name)
 results=json.loads((out/'execution.json').read_text())['rows'];driver.save(out/'controls.json',dict(status='PASS',controls=rows,default_identical=same))
 driver.save(out/'summary.json',dict(status='PASS',kind='AUXILIARY_INTEGER_CONDITIONS',modules=len(json.loads((out/'compiled/modules.json').read_text())),native_cases=len(json.loads((out/'native.json').read_text())),comparisons=sum(r.get('cases',0) for r in results),collections=sum(r.get('moves',0) for r in results),growths=sum(r.get('growths',0) for r in results),inline_checks=sum(r.get('inline_checks',0) for r in results),rejected_controls=len(rows),default_identical_files=len(same),native_zero_traps='retained separately; explicit native condition constructor supplies operation/operands oracle',gate_credit=False));print((out/'summary.json').read_text())
