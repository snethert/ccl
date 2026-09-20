import importlib.util,json,shutil,sys,subprocess
from pathlib import Path

def run(e,out,driver):
 code=driver.generate();rows=[]
 faults=[
 ('drop-left-root','(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)','(i32.store offset=8 ~a (i32.const 0)) (drop ~a) (i32.store offset=12 ~a ~a)','f_add'),
 ('lost-output','(i32.load offset=16 ~a)" root))))))','(i32.load offset=8 ~a)" root))))))','f_add'),
 ('ignore-selected','(i32.and (local.get ~a) (i32.const 31)) (then ~a)','(i32.and (local.get ~a) (i32.const 0)) (then ~a)','h_single'),
 ('wrong-overflow-class','(then (return (i32.const 36)))','(then (return (i32.const 35)))','h_single'),
 ('wrong-underflow-class','(then (return (i32.const 37)))','(then (return (i32.const 38)))','h_single'),
 ('omit-operand-payload','(i32.ne (i32.and (local.get $mask) (i32.const 65536)) (i32.const 0))','(i32.const 0)','h_collect'),
 ('wrong-expected','v (if (< op 4) \'number \'real)','v \'real','h_type'),
 ('lost-condition-root','(i32.store offset=24 (local.get $frame) (local.get $condition))','(i32.store offset=24 (local.get $frame) (i32.const 77825))','h_single'),
 ]
 for name,old,new,why in faults:
  assert code.count(old)>=1,(name,code.count(old));p=out/name
  driver.compile(e,p,code.replace(old,new))
  try:driver.execute(e,p)
  except subprocess.CalledProcessError:
   text=(p/'eager.log').read_text();assert why in text,(name,why,text[-1200:]);rows.append(dict(name=name,status='REJECTED',oracle=why))
  else:raise AssertionError('escaped '+name)
 # Test service policy mistakes against the same compiled modules.
 for name,old,new,why in [
  ('copy-same-format','if(op>=10&&op<=11&&safe<=1','if(false&&op>=10&&op<=11&&safe<=1','f_identity'),
  ('lost-native-overflow','x.integer>=limit||x.integer<=-limit','false','h_single'),
  ('mathematical-infinity','if(special){','if(false&&special){','f_lt'),
 ]:
  p=out/name;p.mkdir();shutil.copytree(out/'compiled',p/'compiled');shutil.copy(out/'native.json',p/'native.json');s=(driver.HERE/'service.mjs').read_text();assert s.count(old)==1
  # Keep immutable proposed sources; change only the derived test copy.
  original=driver.execute
  try:
   # Execute prepares its sources, so intercept the command immediately before
   # Node starts and apply the one retained overlay.
   cmd=driver.command
   def mutated(args,log):
    if str(log).endswith('eager.log'):(p/'service.mjs').write_text(s.replace(old,new))
    return cmd(args,log)
   driver.command=mutated
   try:driver.execute(e,p)
   except subprocess.CalledProcessError:
    text=(p/'eager.log').read_text();assert why in text,(name,why,text[-1200:]);rows.append(dict(name=name,status='REJECTED',oracle=why))
   else:raise AssertionError('escaped '+name)
  finally:driver.command=cmd
 # Default entry points retain their reviewed output despite the new mode.
 spec=importlib.util.spec_from_file_location('float_default',driver.HERE.parent/'generic-dispatch/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old_command=m.command
 def default_command(args,log):
  if log.name=='execution.log':
   for f in (driver.ROOT/'runtime/wasm32').glob('*.mjs'):
    if not (out/'default'/f.name).exists():shutil.copy(f,out/'default'/f.name)
  return old_command(args,log)
 m.command=default_command;m.run(e,out/'default',backend=code)
 same=[]
 for f in sorted((e/'2026-09-19-stage1-generic-dispatch-r1/positive').glob('*')):
  if f.suffix in ['.wat','.wasm']:assert f.read_bytes()==(out/'default/compiled'/f.name).read_bytes(),f.name;same.append(f.name)
 driver.save(out/'controls.json',dict(status='PASS',rows=rows,default_identical=same))
