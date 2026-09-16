"""Single-site compiler omissions; every derivative must compile and execute."""
def mutations(source):
 def change(old,new,count=1):
  assert source.count(old)==count,(old,source.count(old));return source.replace(old,new)
 edits={
 'capture-value-not-cell':('base (b-cell-reference v)))','base (b-read-variable v)))'),
 'inherited-first-slot':('(+ 4 (* 4 n)))','(+ 4 (* 0 n)))'),
 'capture-cells-alias':('(b-at base (+ 1 (* 8 i)))','(b-at base (+ 1 (* 0 i)))'),
 'captured-write-cdr':('(b-at (b-cell-reference root) 3)','(b-at (b-cell-reference root) -1)'),
 'setq-store':('value (b-scalar (second args)) (b-bind-value (first args) (b-local value)) value)', 'value (b-scalar (second args)) (b-bind-value (first args) "(i32.const 77825)") value)'),
 'closure-environment':('(if (zerop n) "(i32.const 77825)" (b-at base 30))','(if (zerop n) "(i32.const 77825)" (b-at base 38))'),
 'closure-code-id':('(global.get $code_~a)) (i32.store offset=8','(i32.and (global.get $code_~a) (i32.const 0))) (i32.store offset=8'),
 'closure-version':('(i32.store offset=12 ~a (i32.const 4))','(i32.store offset=12 ~a (i32.const 8))'),
 'closure-publication':('(b-store wasm32::tcr.alloc_pointer (b-at (b-local p) bytes))','(b-store wasm32::tcr.alloc_pointer (b-local p))'),
 'closure-capacity':('(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) (i64.extend_i32_u ~a))','(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.const ~d)) (i64.extend_i32_u ~a)))'),
 'cell-tag-guard':('(i32.ne (i32.and ~a (i32.const 7)) (i32.const 1))','(i32.and (i32.const 0) (i32.ne (i32.and ~a (i32.const 7)) (i32.const 1)))'),
 'nil-cell-guard':('(i32.eq ~a (i32.const 77825)) (i32.ne (i32.and ~a','(i32.and (i32.const 0) (i32.eq ~a (i32.const 77825))) (i32.ne (i32.and ~a'),
 'environment-header':('(i32.ne (i32.load (local.get $p)) (local.get $header))','(i32.ne (i32.and (i32.load (local.get $p)) (i32.const 255)) (i32.and (local.get $header) (i32.const 255)))'),
 'environment-span':('(i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))','(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))))'),
 'required-capture-initialization':('(b-bind-value v (b-wat "(i32.load offset=~d (local.get $incoming))" (* 4 i)))','(b-bind-value v (b-wat "(i32.and (i32.load offset=~d (local.get $incoming)) (i32.const 0))" (* 4 i)))'),
 'closure-bound-root':('(length *b-bound-vars*))))\n           (wat','(max 0 (1- (length *b-bound-vars*))))))\n           (wat'),
 'exception-ownership':('(write-string restore s)\n             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)','(write-string "" s)\n             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)'),
 }
 return {name:change(*pair) for name,pair in edits.items()}
