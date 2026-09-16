"""Single-site compiler omissions in tail transfer and temporary callable storage."""
def mutations(source):
 result={}
 def change(name,fn,old,new):
  start=source.index('(defun '+fn+' ');end=source.find('\n(defun ',start+1)
  if end<0:end=len(source)
  part=source[start:end];assert part.count(old)==1,(name,part.count(old));result[name]=source[:start]+part.replace(old,new)+source[end:]
 change('tail-as-call','b-tail-transfer','(return_call_indirect $tail_slots (type $tail_entry) (local.get $dispatch_self) (local.get ~a) (local.get $context) (local.get $dispatch_slot))','(return (call_indirect $tail_slots (type $tail_entry) (local.get $dispatch_self) (local.get ~a) (local.get $context) (local.get $dispatch_slot)))')
 change('scalar-tail-context','b-scalar','((*b-tail-position* nil))','((*b-tail-position* t))')
 change('pending-effect-tail','b-multiple','(let ((*b-tail-position* nil)) (b-multiple (first forms)))','(b-multiple (first forms))')
 change('tail-argument-offset','b-tail-transfer','(memory.copy (i32.add (local.get $context) (i32.const 48))','(memory.copy (i32.add (local.get $context) (i32.const 52))')
 change('tail-root-retirement','b-tail-transfer','(b-store wasm32::tcr.root_head "(i32.add (local.get $context) (i32.const 32))")','""')
 change('tail-result-owner','b-tail-transfer','(b-store wasm32::tcr.mv_base "(i32.load offset=4 (local.get $context))")','(b-store wasm32::tcr.mv_base "(i32.load (local.get $context))")')
 change('tail-self-identity','b-tail-transfer','(format s "(i32.store offset=36','(write-string "(local.set $dispatch_self (local.get $self))" s)\n      (format s "(i32.store offset=36')
 change('tail-root-count','b-tail-transfer','(i32.add (i32.const 2) (i32.div_u','(i32.add (i32.const 0) (i32.div_u')
 change('tail-null-entry','b-tail-transfer','(b-condition "(ref.is_null (table.get $tail_slots (local.get $dispatch_slot)))" 4)','""')
 change('tail-table-extent','b-tail-transfer','(b-condition "(i32.ge_u (local.get $dispatch_slot) (table.size $tail_slots))" 4)','""')
 change('wrapper-argument-restore','b-wrapper-restore','(b-store wasm32::tcr.vsp "(local.get $incoming)")','(b-store wasm32::tcr.vsp "(local.get $owner)")')
 change('wrapper-exception-count','b-wrapper-restore','(if exceptional "(local.get $old_count)"','(if exceptional "(i32.const 0)"')
 # Original development defect: context stores preceded full frame preflight.
 start=source.index('(defun b-entry-wrapper');end=source.index('(defun b-wrapper-restore')
 line=next(x for x in source[start:end].splitlines() if '(+ 23 (* 4 bound-words))' in x)
 change('entry-frame-preflight','b-entry-wrapper',line,'')
 change('literal-callable-on-heap','b-literal-apply','((*b-stack-closure* t))','((*b-stack-closure* nil))')
 change('literal-environment-rebase','b-tail-transfer','(i32.store offset=2 (local.get $dispatch_self) (i32.add (local.get $dispatch_self) (i32.const 24)))','(nop)')
 change('literal-frame-extent','b-one-module','(local.set $top (i32.add (local.get $top) (i32.load offset=24 (local.get $context))))','(nop)')
 change('literal-transfer-copy','b-tail-transfer','(format s "(memory.copy (i32.add ~a (local.get ~a)) (i32.sub (local.get $dispatch_self) (i32.const 6)) (i32.const ~d))" arguments bytes ephemeral-bytes)','(write-string "" s)')
 start=source.index('(defun b-one-module');end=source.index('(defun compile-call-module',start)
 line=next(x for x in source[start:end].splitlines() if '(i32.lt_u (local.get $nargs)' in x and 'arity' in x)
 change('tail-callee-arity','b-one-module',line,'')
 change('metadata-root-count','b-one-module',':bound-words (length *b-bound-vars*)',':bound-words (1+ (length *b-bound-vars*))')
 return result

def source_regression(source):
 from pathlib import Path
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text()
 start=source.index('(defun b-normalize-literal-apply');end=source.index('\n;;; One continuation',start)
 return source[:start]+old+source[end:]
