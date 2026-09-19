"""Recompile changed local allocation, rooted retention, and loop transfers."""
import json,subprocess,sys
from pathlib import Path
from backend import generate,replace
MUTANTS=[
 ('reused-local','(format nil "$tmp~d" *temporary-count*)','(format nil "$tmp~d" (mod *temporary-count* 4))','p1:'),
 ('prog1-count-local','(forms (first args)) (saved (temporary))','(forms (first args)) (saved "$value")','p1:'),
 ('unrooted-retention','(b-runtime-roots (b-local base) count) body','(b-runtime-roots (b-local base) "(i32.const 0)") body','p1:'),
 ('lost-retention-result','(b-at base 8))))))))','(b-at base 12))))))))','p1:'),
 ('wrong-loop-entry','(i32.le_u (local.get ~a) (i32.const ~d))','(i32.lt_u (local.get ~a) (i32.const ~d))','loop_list:'),
 ('wrong-go-target','(second entry) (third entry) record)','(second entry) (1+ (third entry)) record)','loop_list:'),
 ('lost-fallthrough','(i32.le_u (local.get ~a) (i32.const ~d))','(i32.eq (local.get ~a) (i32.const ~d))','loop_list:'),
 ('skip-go-unwind','(b-wat "(throw $nonlocal_exit ~a)" record))))\n','(b-wat "(br $tagbody_loop)"))))\n','loop_list: control stack restored'),
]
def run(e,out,h,command):
 out.mkdir();rows=[]
 for name,old,new,oracle in MUTANTS:
  code=generate()
  if name=='skip-go-unwind':
   a=code.index('(defun b-go ');prefix,body=code[:a],code[a:];assert body.count(old)==1;damaged=prefix+body.replace(old,new)
  else:
   assert code.count(old)==1,(name,code.count(old));damaged=code.replace(old,new)
  source=out/(name+'.lisp');source.write_text(damaged)
  try:command([sys.executable,h/'temporary_probe.py',e,out/name,source],out/(name+'.log'))
  except subprocess.CalledProcessError:
   log=out/name/'execution.log';assert log.exists(),(name,'must compile and execute')
   text=log.read_text();assert 'AssertionError' in text and oracle in text,(name,text[-2200:])
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 (out/'controls.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');return rows
