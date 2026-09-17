"""Real compiler mutations for nonlocal transfer and control-record ownership."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1)
  if b<0:b=len(source)
  part=source[a:b];assert part.count(old)==1,(name,part.count(old));result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('catch-tail-transfer','b-catch','(code (let ((*b-tail-position* nil))','(code (let ((*b-tail-position* t))')
 change('throw-values-tail-transfer','b-throw','(let ((*b-tail-position* nil)) (b-multiple values))','(let ((*b-tail-position* t)) (b-multiple values))')
 change('throw-first-value-only','b-throw','(i32.store offset=12 (local.get ~a) (local.get $count))','(i32.store offset=12 (local.get ~a) (i32.const 1))')
 change('throw-payload-offset','b-throw','(i32.add (local.get ~a) (i32.const 48))','(i32.add (local.get ~a) (i32.const 52))')
 change('catch-any-target','b-catch','(if (i32.ne (local.get ~a) ~a) (then (throw_ref (local.get ~a))))','(drop (local.get ~a)) (drop ~a) (drop (local.get ~a))')
 change('catch-count-zero','b-catch','(local.set $count (i32.load offset=12 ~a))','(drop (i32.load offset=12 ~a)) (local.set $count (i32.const 0))')
 change('control-publication','b-control-frame','(b-store wasm32::tcr.handler_checkpoint (b-local base))','""')
 change('control-normal-retirement','b-control-frame','(write-string (b-store wasm32::tcr.handler_checkpoint (b-local head)) s)\n      (write-string (b-store wasm32::tcr.unwind_state (b-wat','(write-string "" s)\n      (write-string (b-store wasm32::tcr.unwind_state (b-wat')
 change('nested-unwind-state','b-control-frame','(b-wat "(i32.load offset=20 (local.get ~a))" base)','"(i32.const 0)"')
 change('wrong-exit-class','b-control-runtime','drop (i32.const 1))','drop (i32.const 2))')
 change('tag-identity','b-control-runtime','(i32.eq (i32.load offset=40 (local.get $p)) (local.get $tag))','(i32.const 1)')
 change('cleanup-as-catch','b-control-runtime','(i32.eq (i32.load offset=4 (local.get $p)) (i32.const 1))','(i32.const 1)')
 change('control-marker','b-control-runtime','(if (i32.ne (i32.load offset=24 (local.get $p)) (i32.const 1128483889)) (then (throw $call_error (i32.const 9))))','')
 change('control-cycle','b-control-runtime','(if (i32.ge_u (local.get $previous) (local.get $p)) (then (throw $call_error (i32.const 9))))','')
 spec=importlib.util.spec_from_file_location('direct_mutants',Path(__file__).parent.parent/'b-direct-context/mutants.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old=m.mutations(source)
 for name in ('internal-through-public-wrapper','tail-as-call','wrapper-exception-count','metadata-root-count'):result[name]=old[name]
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text();a=source.index('(defun b-normalize-literal-apply');b=source.index('\n;;; One continuation',a)
 return source[:a]+old+source[b:]
