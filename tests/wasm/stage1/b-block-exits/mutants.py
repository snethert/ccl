"""Single-site compiler mutations for lexical targets, value transfer and allocation."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1)
  if b<0:b=len(source)
  part=source[a:b];assert part.count(old)==1,(name,part.count(old));result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('block-as-catch','b-local-block','(b-exit-frame 3','(b-exit-frame 1')
 change('block-innermost-identity','b-local-return',"(assoc identity *b-blocks* :test #'eq)","(first *b-blocks*)")
 change('block-drop-values','b-local-return','(i32.mul (local.get $count) (i32.const 4))','(i32.const 0)')
 change('block-drop-count','b-local-return','(i32.store offset=12 ~a (local.get $count))','(i32.store offset=12 ~a (i32.const 1))')
 change('block-tail-return-values','b-local-return','(*b-tail-position* nil)','(*b-tail-position* t)')
 change('exit-tail-body','b-exit-frame','(*b-tail-position* nil)','(*b-tail-position* t)')
 change('exit-match-any','b-exit-frame','(i32.ne (local.get ~a) ~a)','(i32.and (i32.ne (local.get ~a) ~a) (i32.const 0))')
 change('exit-result-count','b-exit-frame','(local.set $count (i32.load offset=12 ~a))','(local.set $count (i32.add (i32.load offset=12 ~a) (i32.const 1)))')
 change('cons-fields','b-cons','(i32.load offset=12 ~a)) (i32.store offset=4 ~a (i32.load offset=8 ~a))','(i32.load offset=8 ~a)) (i32.store offset=4 ~a (i32.load offset=12 ~a))')
 change('cons-car','b-cons','(b-scalar car-form)','(b-wat "(block (result i32) (drop ~a) (i32.const 77825))" (b-scalar car-form))')
 change('cons-cdr','b-cons','(b-scalar cdr-form)','(b-wat "(block (result i32) (drop ~a) (i32.const 77825))" (b-scalar cdr-form))')
 change('cons-short-allocation','b-cons','(b-heap-block 8','(b-heap-block 0')
 change('cons-wrong-tag','b-cons','p root p root))) 1)','p root p root))) 2)')
 change('block-chain-kind','b-control-runtime','(i32.gt_u (i32.load offset=4 (local.get $p)) (i32.const 3))','(i32.gt_u (i32.load offset=4 (local.get $p)) (i32.const 2))')
 spec=importlib.util.spec_from_file_location('direct_mutants',Path(__file__).parent.parent/'b-direct-context/mutants.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old=m.mutations(source)
 for name in ('internal-through-public-wrapper','metadata-root-count'):result[name]=old[name]
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text();a=source.index('(defun b-normalize-literal-apply');b=source.index('\n;;; One continuation',a)
 return source[:a]+old+source[b:]
