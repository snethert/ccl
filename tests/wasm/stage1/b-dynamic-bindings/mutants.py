"""Single-site compiler mutations for dynamic storage and extent restoration."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1)
  if b<0:b=len(source)
  part=source[a:b];assert part.count(old)==1,(name,part.count(old));result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('parameter-extent','b-one-module',"(if dynamic-parameters (b-special-extent #'emit-body) (emit-body))","(emit-body)")
 change('inline-parameter-extent','b-inline-lambda',"(if (some #'b-special-p (append required (list rest) (first auxiliary))) #'b-special-extent #'funcall)","(if nil #'b-special-extent #'funcall)")
 change('keyword-premature-bind','b-stage-value','(if (b-special-p var)','(if nil')
 change('keyword-read-dynamic','b-stage-read','(b-wat "(i32.load ~a)" (b-bound-address var))','(b-wat "(call $special_read ~a)" (b-special-symbol (ccl::var-name var)))')
 change('keyword-supplied-value','b-binding-code','(if (b-special-p var) (b-bind-value var (b-stage-read var)) "")','""')
 change('keyword-supplied-flag','b-binding-code','(when (b-special-p sp) (write-string (b-bind-value sp (b-stage-read sp)) s))','(when nil (write-string (b-bind-value sp (b-stage-read sp)) s))')
 change('progv-prevalidation','b-progv','(drop (call $progv_symbols (i32.load offset=8 ~a) (local.get $top)))','(drop (i32.load offset=8 ~a))')
 change('progv-revalidation','b-progv','(drop (call $progv_symbols (local.get ~a) (local.get $top)))','(drop (local.get ~a))')
 change('progv-missing-value','b-progv','(local.set ~a (i32.const 51))','(local.set ~a (i32.const 77825))')
 change('progv-value-advance','b-progv','vals next-value)','next-value next-value)')
 change('progv-flags','b-progv-runtime','(if (i32.or (i32.and (local.get $bits) (i32.const 3)) (i32.and (local.get $bits) (i32.const 24))) (then (throw $call_error (i32.const 12))))','')
 change('progv-cycle','b-progv-runtime','(if (i32.and (i32.ne (local.get $p) (i32.const 77825)) (i32.eq (local.get $p) (local.get $slow))) (then (throw $call_error (i32.const 12))))','')
 change('progv-preflight-capacity','b-progv-runtime','(if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 32))) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $call_error (i32.const 2))))','')
 change('dynamic-tail-transfer','b-special-extent','(*b-tail-position* nil)','(*b-tail-position* t)')
 change('normal-unbind','b-special-extent','(format s "(call $unbind_to (local.get ~a))','(format s "(drop (local.get ~a))')
 change('exception-unbind','b-special-extent','(local.set ~a) (call $unbind_to (local.get ~a))','(local.set ~a) (drop (local.get ~a))')
 change('old-binding-value','b-bind-symbol','(i32.load (local.get ~a)))','(block (result i32) (drop (local.get ~a)) (i32.const 243)))')
 change('binding-publication','b-bind-symbol','(b-store wasm32::tcr.db_link (b-local base))','""')
 change('binding-root-count','b-bind-symbol','"(i32.const 2)"','"(i32.const 1)"')
 spec=importlib.util.spec_from_file_location('direct_mutants',Path(__file__).parent.parent/'b-direct-context/mutants.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old=m.mutations(source)
 for name in ('internal-through-public-wrapper','metadata-root-count'):result[name]=old[name]
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text();a=source.index('(defun b-normalize-literal-apply');b=source.index('\n;;; One continuation',a)
 return source[:a]+old+source[b:]
