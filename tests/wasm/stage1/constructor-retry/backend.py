"""Rooted retry for binding vectors, restarts and implicit conditions."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('constructor_retry_prior',HERE.parent/'allocation-retry/backend.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace;base=prior.base

def end_form(s,start):
 depth=0;string=False;escape=False;comment=False
 for i in range(start,len(s)):
  c=s[i]
  if comment:
   if c=='\n':comment=False
  elif string:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':string=False
  elif c==';':comment=True
  elif c=='"':string=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if not depth:return i+1
 raise AssertionError('unclosed form')
def variant(s,name,transform):
 a=s.index('(defun '+name+' ');b=end_form(s,a);f=s[a:b];h=end_form(f,f.index('(',7));old=f[h:-1];new=transform(old);assert old!=new,name
 return s[:a]+f[:h]+'\n (if *b-allocation-retry* (progn '+new+') (progn '+old+')))'+s[b:]
def ensure(bytes):
 return '(if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.extend_i32_u '+bytes+')) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure '+bytes+')))\n '
BIND='''
  (let ((value (temporary)) (base (temporary)) (slot (temporary)))
    (with-output-to-string (s)
      ;; Stage in the eventual binding record before vector growth can collect.
      (format s "(local.set ~a ~a) (local.set ~a (local.get $top))" value code base)
      (write-string (b-reserve-runtime "(i64.const 32)") s)
      (write-string (b-runtime-roots (b-at (b-local base) 8) "(i32.const 2)") s)
      (format s "(i32.store offset=16 (local.get ~a) ~a) (i32.store offset=20 (local.get ~a) (local.get ~a)) (local.set ~a (call $dynamic_slot (i32.load offset=16 (local.get ~a))))"
        base symbol base value slot base)
      ;; No call between reading the moved value and publishing the binding.
      (format s "(local.set ~a (i32.load offset=20 (local.get ~a))) (i32.store (local.get ~a) ~a) (i32.store offset=4 (local.get ~a) (i32.load offset=22 (i32.load offset=16 (local.get ~a)))) (i32.store offset=24 (local.get ~a) (i32.const 1112425521)) (i32.store offset=28 (local.get ~a) (i32.const 0)) (i32.store offset=20 (local.get ~a) (i32.load (local.get ~a)))"
        value base base (b-load wasm32::tcr.db_link) base base base base base slot)
      (write-string (b-store wasm32::tcr.db_link (b-local base)) s)
      (format s "(i32.store (local.get ~a) (local.get ~a))" slot value)))
'''
def dynamic(s):
 old='  (local.set $p (i32.load offset=48 (global.get $tcr)))'
 new='  '+ensure('(i32.and (i32.add (i32.mul (local.get $newcap) (i32.const 4)) (i32.const 11)) (i32.const -8))')+'(local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))\n'+old
 return replace(s,old,new)
def progv_runtime(s):
 # Checking a list's symbols must not allocate: its raw scan cursors are locals.
 return replace(s,'(call $dynamic_slot (local.get $symbol)))','(if (i32.eqz (call $binding_index (local.get $symbol))) (then (throw $call_error (i32.const 11))))\n     (call $binding_index (local.get $symbol)))')
def progv(s):
 old='(write-string (b-bind-symbol (b-local symbol) (b-local value)) out)'
 new='''(format out "(i32.store offset=12 ~a (local.get ~a))" base vals)
                (write-string (b-bind-symbol (b-local symbol) (b-local value)) out)
                (format out "(local.set ~a (i32.load offset=12 ~a))" vals base)'''
 return replace(s,old,new)
def restart(s):
 old='(func $restart_make (param $name i32) (param $action i32) (param $top i32) (result i32) (local $p i32)'
 new='(func $restart_make (param $arguments i32) (result i32) (local $name i32) (local $action i32) (local $p i32)\n '+ensure('(i32.const 32)')+'(local.set $name (i32.load (local.get $arguments))) (local.set $action (i32.load offset=4 (local.get $arguments)))'
 return replace(s,old,new)
def condition(s):
 s=replace(s,'(func $condition_new (param $mask i32) (param $datum i32) (param $expected i32) (result i32)','(func $condition_new (param $mask i32) (param $arguments i32) (result i32) (local $datum i32) (local $expected i32)')
 old=' (local.set $p (i32.load offset=48 (global.get $tcr)))'
 new=' '+ensure('(local.get $bytes)')+'''(local.set $row (call $condition_row (local.get $mask) (i32.const 0)))
 (local.set $defaults (i32.sub (i32.load offset=12 (local.get $row)) (i32.const 6)))
 (local.set $datum (i32.load (local.get $arguments))) (local.set $expected (i32.load offset=4 (local.get $arguments)))
'''+old
 return replace(s,old,new)
def generate():
 s=prior.generate()
 for name,change in [('b-bind-symbol',lambda _:BIND),('b-dynamic-runtime',dynamic),('b-progv',progv),('b-progv-runtime',progv_runtime),('b-restart-runtime',restart),('b-condition-runtime',condition)]:s=variant(s,name,change)
 s=variant(s,'b-restart-call',lambda x:replace(x,'(b-wat "(call $restart_make ~a ~a (local.get $top))" (arg 0) (arg 1))','(b-wat "(call $restart_make (i32.add ~a (i32.const 8)))" root)'))
 s=variant(s,'b-implicit-runtime',lambda x:replace(x,'(local.get $datum) (local.get $expected))) (i32.store (local.get $results)','(i32.add (local.get $frame) (i32.const 8)))) (i32.store (local.get $results)'))
 return s
if __name__=='__main__':print(generate())
