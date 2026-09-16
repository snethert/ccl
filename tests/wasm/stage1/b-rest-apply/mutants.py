def mutations(source):
 def one(old,new):
  assert source.count(old)==1,(old,source.count(old));return source.replace(old,new)
 edits={
 'rest-order':('(i32.mul (local.get ~a) (i32.const 4))))) (local.set ~a (i32.add (local.get ~a) (i32.const 1)))', '(i32.mul (i32.sub (i32.sub (local.get $nargs) (i32.const 1)) (local.get ~a)) (i32.const 4))))) (local.set ~a (i32.add (local.get ~a) (i32.const 1)))'),
 'rest-cdr':('(i32.store (local.get ~a) (local.get ~a)) (i32.store offset=4', '(i32.store (local.get ~a) (i32.or (i32.const 77825) (i32.and (local.get ~a) (i32.const 0)))) (i32.store offset=4'),
 'rest-publish':('(write-string (b-bind-value var (b-local head)) s)', '(write-string (b-bind-value var "(i32.const 77825)") s)'),
 'rest-pointer':('(b-store wasm32::tcr.alloc_pointer (b-local cursor))','(b-store wasm32::tcr.alloc_pointer (b-load wasm32::tcr.alloc_pointer))'),
 'rest-heap-capacity':('(i64.gt_u (local.get $wide) (i64.extend_i32_u ~a))', '(i32.and (i32.const 0) (i64.gt_u (local.get $wide) (i64.extend_i32_u ~a)))'),
 'rest-alignment':('(i32.and (local.get ~a) (i32.const 7)))', '(i32.and (local.get ~a) (i32.const 0)))'),
 'incoming-extent':('(i64.mul (i64.extend_i32_u (local.get $nargs)) (i64.const 4)) (i64.const 15)', '(i64.extend_i32_u (i32.mul (local.get $nargs) (i32.const 4))) (i64.const 15)'),
 'apply-prefix-order':("(codes (mapcar #'b-scalar prefix))", "(codes (mapcar #'b-scalar (reverse prefix)))"),
 'apply-list-tag':('(i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d))', '(i32.and (i32.const 0) (i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d)))'),
 'apply-list-memory':('(i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.const 7)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))', '(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.const 7)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))))'),
 'apply-cycle':('(i32.and (i32.ne (local.get ~a) (i32.const 77825)) (i32.eq (local.get ~a) (local.get ~a)))', '(i32.and (i32.const 0) (i32.and (i32.ne (local.get ~a) (i32.const 77825)) (i32.eq (local.get ~a) (local.get ~a))))'),
 'apply-frame-capacity':('(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.add (local.get $wide) (i64.const 256))) (i64.extend_i32_u ~a))', '(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (i64.add (local.get $wide) (i64.const 256))) (i64.extend_i32_u ~a)))'),
 'apply-car':('(i32.load offset=3 (local.get ~a))) (local.set ~a (i32.load (i32.sub', '(i32.load (i32.sub (local.get ~a) (i32.const 1)))) (local.set ~a (i32.load (i32.sub'),
 'apply-count':('(local.set ~a (i32.add (local.get ~a) (i32.const ~d))) (local.set ~a (local.get $top)) (local.set $wide', '(local.set ~a (i32.add (i32.and (local.get ~a) (i32.const 63)) (i32.const ~d))) (local.set ~a (local.get $top)) (local.set $wide'),
 'apply-result-copy':('(memory.copy (local.get $results) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))', '(memory.copy (local.get $results) (local.get ~a) (i32.const 4))'),
 'apply-result-scanner':('(i32.div_u (i32.sub (i32.wrap_i64 (local.get $wide)) (i32.const 8)) (i32.const 4))', '(i32.div_u (i32.sub (i32.wrap_i64 (local.get $wide)) (i32.const 4)) (i32.const 4))'),
 'apply-tail-twice':('(format s "(i32.store offset=12 (local.get ~a) ~a) (local.set ~a', '(format s "(i32.store offset=12 (local.get ~a) ~a) (local.set ~a'),
 'arity-64':('(if (or keys rest) #xffffffff maximum)', '(if (or keys rest) 64 maximum)'),
 }
 # Format argument count retained: inject a second evaluation directly into
 # the emitted tail string, without changing which value is finally used.
 edits['apply-tail-twice']=("(tail (b-scalar (first (second argument-list)))))", "(tail (let ((code (b-scalar (first (second argument-list))))) (b-wat \"(block (result i32) (drop ~a) ~a)\" code code))))")
 return {name:one(old,new) for name,(old,new) in edits.items()}
