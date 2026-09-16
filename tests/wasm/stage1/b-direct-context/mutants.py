"""Compiler controls for direct continuation preparation and internal calls."""
import importlib.util
from pathlib import Path

def mutations(source):
 result={}
 def change(name,fn,old,new):
  start=source.index('(defun '+fn+' ');end=source.find('\n(defun ',start+1)
  if end<0:end=len(source)
  part=source[start:end];assert part.count(old)==1,(name,part.count(old));result[name]=source[:start]+part.replace(old,new)+source[end:]
 change('internal-through-public-wrapper','b-internal-dispatch','(b-wat "(call_indirect $tail_slots (type $tail_entry) (local.get $dispatch_self) ~a ~a (local.get $dispatch_slot))" count context)','(b-wat "(call_indirect (type $b_entry) (local.get $dispatch_self) ~a (local.get $dispatch_slot))" count)')
 change('direct-argument-offset','b-internal-call','(+ 48 (* 4 i))','(+ 52 (* 4 i))')
 change('direct-results-source','b-internal-call','base)\n      (write-string (b-store wasm32::tcr.vsp','context)\n      (write-string (b-store wasm32::tcr.vsp')
 change('direct-root-restore','b-internal-call','(b-store wasm32::tcr.root_head (b-local root))','(b-store wasm32::tcr.root_head (b-local context))')
 change('context-root-count','b-prepare-context','(i32.add (i32.const 2) ~a)','(i32.add (i32.const 1) ~a)')
 change('context-tail-output','b-prepare-context','context output context context','context context context context')
 change('context-wrong-self-root','b-internal-call','(i32.store offset=40 (local.get ~a) (local.get $dispatch_self))','(i32.store offset=40 (local.get ~a) (i32.const 77825))')
 change('internal-null-entry','b-internal-dispatch','(b-condition "(ref.is_null (table.get $tail_slots (local.get $dispatch_slot)))" 4)','""')
 change('internal-table-extent','b-internal-dispatch','(b-condition "(i32.ge_u (local.get $dispatch_slot) (table.size $tail_slots))" 4)','""')
 change('apply-direct-spread-offset','b-internal-apply','(i32.add (i32.const 48) (i32.mul','(i32.add (i32.const 52) (i32.mul')
 change('apply-prefix-copy','b-internal-apply','(* 4 n) cursor evaluated index n)','0 cursor evaluated index n)')
 # Omit only the relink while retaining the saved-root field for an independent
 # layout check at internal entry. Two local.get operands become a harmless drop.
 change('apply-root-retirement','b-internal-apply','(i32.store offset=32 (local.get ~a) (local.get ~a))','(drop (i32.add (local.get ~a) (local.get ~a)))')
 # Reuse meaningful checks of unchanged tail/public-boundary mechanisms.
 spec=importlib.util.spec_from_file_location('reviewed_tail_mutants',Path(__file__).parent.parent/'b-tail-calls/mutants.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 old=module.mutations(source)
 for name in ('tail-as-call','scalar-tail-context','pending-effect-tail','wrapper-argument-restore','wrapper-exception-count','literal-frame-extent','tail-callee-arity','metadata-root-count'):
  result[name]=old[name]
 return result

def source_regression(source):
 from pathlib import Path
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text()
 start=source.index('(defun b-normalize-literal-apply');end=source.index('\n;;; One continuation',start)
 return source[:start]+old+source[end:]
