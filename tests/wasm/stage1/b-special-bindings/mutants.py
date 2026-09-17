"""Single-site compiler mutations for dynamic storage and extent restoration."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1)
  if b<0:b=len(source)
  part=source[a:b];assert part.count(old)==1,(name,part.count(old));result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('special-as-lexical','b-special-p','(and var (logbitp ccl::$vbitspecial (ccl::nx-var-bits var)))','(and var nil)')
 change('parallel-as-sequential','b-let','(b-frame (length (first args))',"(setq op 'ccl::let*) (b-frame (length (first args))")
 change('dynamic-tail-transfer','b-special-extent','(*b-tail-position* nil)','(*b-tail-position* t)')
 change('normal-unbind','b-special-extent','(format s "(call $unbind_to (local.get ~a))','(format s "(drop (local.get ~a))')
 change('exception-unbind','b-special-extent','(local.set ~a) (call $unbind_to (local.get ~a))','(local.set ~a) (drop (local.get ~a))')
 change('old-binding-value','b-special-bind','(i32.load (local.get ~a)))','(block (result i32) (drop (local.get ~a)) (i32.const 243)))')
 change('binding-publication','b-special-bind','(b-store wasm32::tcr.db_link (b-local base))','""')
 change('binding-root-count','b-special-bind','"(i32.const 2)"','"(i32.const 1)"')
 change('binding-symbol-slot','b-special-bind','(i32.store offset=16 (local.get ~a) ~a)','(i32.store offset=20 (local.get ~a) ~a)')
 change('restore-symbol-as-value','b-dynamic-runtime','(i32.store (local.get $slot) (i32.load offset=20 (local.get $p)))','(i32.store (local.get $slot) (i32.load offset=16 (local.get $p)))')
 change('global-only','b-dynamic-runtime','(i32.eq (i32.load (local.get $slot)) (i32.const 243))','(i32.const 1)')
 change('local-only','b-dynamic-runtime','(i32.eq (i32.load (local.get $slot)) (i32.const 243))','(i32.const 0)')
 change('unbound-value','b-dynamic-runtime','(if (i32.eq (local.get $value) (i32.const 51)) (then (throw $call_error (i32.const 10))))','')
 change('setq-function-cell','b-scalar-inner','(call $special_location ~a)','(i32.add ~a (i32.const 6))')
 change('tcr-index-for-symbol','b-dynamic-runtime','(local.set $index (i32.load offset=22 (local.get $symbol)))','(local.set $index (i32.shl (i32.load (global.get $tcr)) (i32.const 2)))')
 change('reserved-binding-index','b-dynamic-runtime','(i32.le_s (local.get $index) (i32.const 0))','(i32.lt_s (local.get $index) (i32.const 0))')
 change('binding-vector-extent','b-dynamic-runtime','(if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $base)) (i64.mul (i64.extend_i32_u (local.get $cap)) (i64.const 4))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 11))))','')
 spec=importlib.util.spec_from_file_location('direct_mutants',Path(__file__).parent.parent/'b-direct-context/mutants.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old=m.mutations(source)
 for name in ('internal-through-public-wrapper','metadata-root-count'):result[name]=old[name]
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text();a=source.index('(defun b-normalize-literal-apply');b=source.index('\n;;; One continuation',a)
 return source[:a]+old+source[b:]
