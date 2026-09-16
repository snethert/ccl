def mutations(source):
 prefix,body=source.split(';;; First B call unit:',1)
 def one(text,old,new):
  assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)
 edits={
 'argument-order':('(loop for code in codes for i from 0','(loop for code in (reverse codes) for i from 0'),
 'argument-stride':('(+ 16 (* 4 i)) base code','(+ 16 (* 8 i)) base code'),
 'result-copy':('(memory.copy (local.get $results) (i32.add (local.get ~a) (i32.const ~d)) (i32.mul (local.get $count) (i32.const 4)))','(memory.copy (local.get $results) (i32.add (local.get ~a) (i32.const ~d)) (i32.const 4))'),
 'exception-count':('(b-store wasm32::tcr.mv_count "(local.get $old_count)")','(b-store wasm32::tcr.mv_count "(i32.const 1)")'),
 'result-count':('(b-store wasm32::tcr.mv_count "(local.get $count)")','(b-store wasm32::tcr.mv_count "(i32.const 0)")'),
 'zero-primary':('(else (i32.const 77825)))) (memory.copy','(else (i32.const 0)))) (memory.copy'),
 'saved-values-count':('(local.set $count (local.get ~a)) (memory.copy (local.get $results) ~a','(local.set $count (i32.and (local.get ~a) (i32.const 1))) (memory.copy (local.get $results) ~a'),
 'double-scanner':('(b-initialize-roots (b-local base) (+ 2 arg-slots))','(b-initialize-roots (b-local base) (+ 3 arg-slots))'),
 'root-restoration':('(b-store wasm32::tcr.root_head "(local.get $root)")','(b-store wasm32::tcr.root_head "(i32.const 0)")'),
 'vsp-restoration':('(b-store wasm32::tcr.vsp "(local.get $incoming)")','(b-store wasm32::tcr.vsp "(local.get $output)")'),
 'owner-restoration':('(b-store wasm32::tcr.mv_owner_top "(local.get $owner)")','(b-store wasm32::tcr.mv_owner_top "(i32.sub (local.get $owner) (i32.const 16))")'),
 'arity-check':('(i32.ne (local.get $nargs) (i32.const ~d))','(i32.lt_u (local.get $nargs) (i32.const ~d))'),
 'result-capacity':('(i64.mul (i64.extend_i32_u (local.get $count)) (i64.const 4))) (i64.extend_i32_u (local.get $owner)))','(i64.mul (i64.extend_i32_u (local.get $count)) (i64.const 0))) (i64.extend_i32_u (local.get $owner)))'),
 }
 # A duplicate evaluation, retaining FORMAT's argument count and order.
 edits['argument-twice']=('(loop for code in codes for i from 0 do (format s "(i32.store offset=~d (local.get ~a) ~a)" (+ 16 (* 4 i)) base code))','(loop for code in codes for i from 0 do (format s "(drop ~a) (i32.store offset=~d (local.get ~a) ~a)" code (+ 16 (* 4 i)) base code))')
 # Keep the wide comparison syntactically valid; disabling its failure branch
 # must be exposed by a genuine too-small VSP limit.
 edits['stack-capacity']=('(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.const ~d)) (i64.extend_i32_u ~a))','(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.const ~d)) (i64.extend_i32_u ~a)))')
 return {name:prefix+';;; First B call unit:'+one(body,old,new) for name,(old,new) in edits.items()}
