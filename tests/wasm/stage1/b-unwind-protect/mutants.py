"""Compile semantic mutations through real CCL pass 2; unchanged execution oracle."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,old,new):
  start=source.index('(defun b-unwind-protect ');end=source.index('\n(defun b-scalar ',start)
  part=source[start:end];assert part.count(old)==1,(name,part.count(old));result[name]=source[:start]+part.replace(old,new)+source[end:]
 change('normal-cleanup-omitted','(write-string cleanup-code out)','(write-string "" out)')
 change('normal-cleanup-duplicated','(write-string cleanup-code out)','(write-string cleanup-code out) (write-string cleanup-code out)')
 change('exception-cleanup-omitted','protected-code exception restore cleanup-code exception','protected-code exception restore "" exception')
 change('exception-identity','(throw_ref (local.get ~a)))','(drop (local.get ~a)) (throw $call_error (i32.const 1)))')
 change('saved-values-omitted','saved-count (b-at retained 8))\n            (write-string restore', 'saved-count "(local.get $results)")\n            (write-string restore')
 change('saved-count-zero','(local.set ~a (local.get $count)) (memory.copy','(local.set ~a (i32.const 0)) (memory.copy')
 change('protected-tail-transfer','(protected-code (let ((*b-tail-position* nil))','(protected-code (let ((*b-tail-position* t))')
 change('cleanup-tail-transfer','(cleanup-code (let ((*b-tail-position* nil))','(cleanup-code (let ((*b-tail-position* t))')
 change('cleanup-top-restore','(b-wat "(local.set $top (local.get ~a))" top)','""')
 change('cleanup-root-restore','(b-store wasm32::tcr.root_head (b-local root))','""')
 change('cleanup-vsp-restore','(b-store wasm32::tcr.vsp (b-local vsp))','""')
 change('cleanup-root-count','(b-retained-frame "(local.get $capacity)"','(b-retained-frame "(i32.const 0)"')
 spec=importlib.util.spec_from_file_location('direct_mutants',Path(__file__).parent.parent/'b-direct-context/mutants.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 inherited=m.mutations(source)
 for name in ('internal-through-public-wrapper','direct-argument-offset','apply-prefix-copy','tail-as-call','wrapper-exception-count','metadata-root-count'):
  result[name]=inherited[name]
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text()
 start=source.index('(defun b-normalize-literal-apply');end=source.index('\n;;; One continuation',start)
 return source[:start]+old+source[end:]
