"""Recompile faults; require a focused runtime or instruction-shape failure."""
import json,subprocess,sys
from pathlib import Path
from backend import generate
# Only one focused case executes per mutant. The unchanged full unit still compiles.
MUTANTS=[
 ('unsafe-branch','(unless (b-branch-tagbody-p tags forms)','(unless t','local_cleanup','local_cleanup:'),
 ('wrong-branch-destination','(second entry) (third entry) (fifth entry)','(second entry) (1+ (third entry)) (fifth entry)','fast_choices_t','fast_choices_t:'),
 ('skip-branch','(local.set ~a (i32.const ~d)) (br ~a)','(local.set ~a (i32.const ~d)) (block ~a)','fast_loop_4000','fast_loop_4000:'),
 ('lost-branch-fallthrough','(i32.le_u (local.get ~a) (i32.const ~d))','(i32.eq (local.get ~a) (i32.const ~d))','fast_fallthrough','fast_fallthrough:'),
 ('captured-cell-stale','(b-wat "(i32.load offset=~d (i32.sub (i32.load offset=2 (i32.load offset=40 (local.get $context))) (i32.const 6)))" (+ 4 (* 4 n)))','(b-wat "(i32.load offset=~d (local.get $closure_env))" (+ 4 (* 4 n)))','closed_mutable','closed_mutable:'),
 ('unnecessary-unwind','(unless (b-branch-tagbody-p tags forms)','(unless nil','fast_loop_4000','fast_loop no direct loop'),
 ('expired-target-match','(i32.eq (i32.load offset=40 (local.get $p)) (local.get $tag))','(i32.const 1)','closed_nearest','closed_nearest:'),
]
def run(e,out,h,command):
 out.mkdir();rows=[]
 for name,old,new,case,oracle in MUTANTS:
  code=generate()
  if name=='lost-branch-fallthrough':
   a=code.index('(defun b-tagbody (tags forms)');prefix,part=code[:a],code[a:];assert part.count(old)==1;code=prefix+part.replace(old,new)
  else:
   assert code.count(old)==1,(name,code.count(old));code=code.replace(old,new)
  src=out/(name+'.lisp');src.write_text(code)
  probe=out/(name+'.py');text=(h/'transfer_probe.py').read_text();text=text.replace("if __name__=='__main__':", "_all_cases=errors.cases\nerrors.cases=lambda:[r for r in _all_cases() if r['id']=="+repr(case)+"]\nif __name__=='__main__':");probe.write_text('import sys\nsys.path.insert(0,'+repr(str(h))+')\n'+text)
  try:command([sys.executable,probe,e,out/name,src],out/(name+'.log'))
  except subprocess.CalledProcessError:
   log=out/name/'execution.log';assert log.exists(),(name,'must compile and execute', (out/(name+'.log')).read_text()[-2000:])
   t=log.read_text();assert 'AssertionError' in t and oracle in t,(name,t[-2200:])
  else:
   if name!='unnecessary-unwind':raise AssertionError(name+' escaped')
   from shape import inspect
   try:inspect(out/name/'compiled')
   except AssertionError as ex:assert str(ex)==oracle,str(ex)
   else:raise AssertionError(name+' shape control escaped')
  rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 (out/'controls.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');return rows
