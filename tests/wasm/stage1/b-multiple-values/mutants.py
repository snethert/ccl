"""Single-site mutations of value collection, rooted continuations and value binding."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1)
  if b<0:b=len(source)
  part=source[a:b];assert part.count(old)==1,(name,part.count(old));result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('mvc-reverse-producers','b-multiple-call',"(dolist (code codes)","(dolist (code (reverse codes))")
 change('mvc-callee-primary','b-multiple-call','(self (b-scalar callee))','(self (b-wat "(block (result i32) (drop ~a) (i32.const 77825))" (b-scalar callee)))')
 change('mvc-tail-producers','b-multiple-call','(*b-tail-position* nil)','(*b-tail-position* t)')
 change('mvc-copy-offset','b-multiple-call','context n)','context slots)')
 change('mvc-drop-values','b-multiple-call','(local.get $results) (i32.mul (local.get $count) (i32.const 4)))','(local.get $results) (i32.const 0))')
 change('mvc-drop-accumulation','b-multiple-call','(local.set ~a (i32.add (local.get ~a) (local.get $count)))','(local.set ~a (i32.add (i32.and (local.get ~a) (i32.const 0)) (local.get $count)))')
 change('mvc-count-padding','b-multiple-call','(b-internal-dispatch (b-local context) (b-local n))','(b-internal-dispatch (b-local context) (b-local slots))')
 change('mvc-tail-count','b-multiple-call','(b-tail-transfer (b-at (b-local context) 48) (b-local n))','(b-tail-transfer (b-at (b-local context) 48) (b-local slots))')
 change('mvc-short-root-range','b-multiple-call','(i32.store offset=36 (local.get ~a) (i32.add (i32.const 2) (local.get ~a)))','(i32.store offset=36 (local.get ~a) (i32.add (i32.const 0) (local.get ~a)))')
 change('mvc-no-tail','b-multiple-call','(if *b-tail-position*\n        (write-string (b-tail-transfer','(if nil\n        (write-string (b-tail-transfer')
 change('mvb-zero-pad','b-multiple-bind','(else (i32.const 77825))','(else (i32.const 0))')
 change('mvb-inclusive-count','b-multiple-bind','(i32.gt_u (local.get $count)','(i32.ge_u (local.get $count)')
 change('mvb-reverse-slots','b-multiple-bind','(+ 8 (* 4 i)) base)) s))','(+ 8 (* 4 (- (length (first args)) i 1))) base)) s))')
 change('mvb-tail-value-form','b-multiple-bind','(*b-tail-position* nil)','(*b-tail-position* t)')
 change('mvb-no-special-unwind','b-multiple-bind',"(b-special-extent #'body)","(body)")
 spec=importlib.util.spec_from_file_location('direct_mutants',Path(__file__).parent.parent/'b-direct-context/mutants.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old=m.mutations(source)
 for name in ('internal-through-public-wrapper','metadata-root-count'):result[name]=old[name]
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text();a=source.index('(defun b-normalize-literal-apply');b=source.index('\n;;; One continuation',a)
 return source[:a]+old+source[b:]
