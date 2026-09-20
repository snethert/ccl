"""Recompile real front-end input; require executed semantic refusals."""
import importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def execute(e,out,driver,service=None):
 for n in ['collector-owner.mjs','binary.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['service.mjs','execute.mjs']:shutil.copy(HERE/n,out/n)
 if service is not None:(out/'service.mjs').write_text(service)
 driver.command(['/usr/local/bin/node',out/'execute.mjs',out,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm',out/'execution.json'],out/'execution.log')
def run(e,out,driver):
 execute(e,out,driver);rows=[];code=driver.generate();base=(HERE/'service.mjs').read_text()
 faults=[
  ('fixnum-bound','(i64.const 536870911)','(i64.const 536870912)','n_mul'),
  ('negative-length','(i32.xor (local.get $a) (i32.shr_s (local.get $a) (i32.const 31)))','(local.get $a)','n_length'),
  ('right-shift-mask','(select (i32.const 31) (i32.sub (i32.const 0) (local.get $b)) (i32.le_s (local.get $b) (i32.const -31)))','(i32.sub (i32.const 0) (local.get $b))','n_ash'),
  ('truncate-count','(local.set $count (i32.const 2))))\n  (br_if $slow','(local.set $count (i32.const 1))))\n  (br_if $slow','n_truncate'),
  ('remainder-dropped','(i32.shl (i32.wrap_i64 (local.get $rem)) (i32.const 2))','(i32.const 0)','n_truncate'),
  ('operand-order','root (b-scalar (first forms)) root (if (= op 4) "(i32.const 0)" (b-scalar (second forms)))','root (if (= op 4) (b-scalar (first forms)) (b-scalar (second forms))) root (if (= op 4) "(i32.const 0)" (b-scalar (first forms)))','n_sub'),
 ]
 for name,old,new,why in faults:
  assert code.count(old)==1,(name,code.count(old));path=out/name;driver.compile(e,path,code.replace(old,new))
  try:execute(e,path,driver)
  except subprocess.CalledProcessError:
   text=(path/'execution.log').read_text();assert why in text,(name,text[-2000:]);rows.append(dict(name=name,oracle=why,status='REJECTED'))
  else:raise AssertionError('escaped '+name)
 ownerfaults=[
  ('stale-allocation','const heap=get(tcr+48),limit=get(tcr+52);','const heap=oldHeap,limit=get(tcr+52);','n_mul/76 code 6'),
  ('missing-second-root','set(root+12,bResult);','set(root+12,0);','n_truncate'),
  ('publication-missing','set(tcr+48,heap+size);','/* omitted allocation publication */','n_nested/80 code 32'),
 ]
 for name,old,new,why in ownerfaults:
  assert base.count(old)==1;changed=base.replace(old,new)
  if name=='stale-allocation':changed=changed.replace('   if(size){try{','   const oldHeap=get(tcr+48);\n   if(size){try{')
  path=out/name;path.mkdir();shutil.copytree(out/'compiled',path/'compiled');shutil.copy(out/'native.json',path/'native.json')
  try:execute(e,path,driver,changed)
  except subprocess.CalledProcessError:
   text=(path/'execution.log').read_text();assert why in text,(name,why,text[-2000:]);rows.append(dict(name=name,oracle=why,status='REJECTED'))
  else:raise AssertionError('escaped '+name)
 # Default API is byte-identical on the reviewed 30-module dispatch corpus.
 legacy=load('integer_default_legacy',HERE.parent/'generic-dispatch/run.py');legacy.run(e,out/'default',backend=code)
 old=e/'2026-09-19-stage1-generic-dispatch-r1/positive';same=[]
 for f in sorted(old.glob('*')):
  if f.suffix in ['.wat','.wasm']:
   assert f.read_bytes()==(out/'default/compiled'/f.name).read_bytes(),f.name;same.append(f.name)
 driver.save(out/'controls.json',dict(status='PASS',mutants=rows,default_identical=same))
 results=json.loads((out/'execution.json').read_text())['rows']
 driver.save(out/'summary.json',dict(status='PASS',kind='AUXILIARY_GENERATED_INTEGER_CALLS',modules=len(json.loads((out/'compiled/modules.json').read_text())),native_cases=len(json.loads((out/'native.json').read_text())),comparisons=sum(r.get('cases',0) for r in results),collections=sum(r.get('moves',0) for r in results),growths=sum(r.get('growths',0) for r in results),mutants=len(rows),default_identical_files=len(same),gate_credit=False))
 print((out/'summary.json').read_text())
