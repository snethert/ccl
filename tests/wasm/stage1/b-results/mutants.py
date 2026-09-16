def mutations(source):
 def one(old,new):
  assert source.count(old)==1,(old,source.count(old));return source.replace(old,new)
 edits={
 'fixed-64-budget':('(local.set $capacity (i32.div_u (local.get $result_bytes) (i32.const 4)))','(local.set $capacity (i32.const 64))'),
 'fixed-root-count':('(i32.add (local.get $capacity) (i32.const ~d))','(i32.add (i32.const 64) (i32.const ~d))'),
 'fixed-binding-offset':('(i32.add (local.get $frame) (i32.add (i32.const 8) (local.get $result_bytes)))','(i32.add (local.get $frame) (i32.const 264))'),
 'scratch-offset':('(local.set $results (i32.add (local.get $frame) (i32.const 8)))','(local.set $results (i32.add (local.get $frame) (i32.const 12)))'),
 'values-copy-primary':('(memory.copy (local.get $results) ~a (i32.const ~d))','(memory.copy (local.get $results) ~a (i32.and (i32.const ~d) (i32.const 4)))'),
 'values-capacity':('(i32.gt_u (i32.const ~d) (local.get $capacity))','(i32.and (i32.const 0) (i32.gt_u (i32.const ~d) (local.get $capacity)))'),
 'retained-copy-64':('(memory.copy ~a (local.get $results) (i32.mul (local.get ~a) (i32.const 4)))','(memory.copy ~a (local.get $results) (i32.mul (i32.and (local.get ~a) (i32.const 63)) (i32.const 4)))'),
 'retained-count':('(local.set $count (local.get ~a)) (memory.copy (local.get $results) ~a','(local.set $count (i32.and (local.get ~a) (i32.const 1))) (memory.copy (local.get $results) ~a'),
 'retained-extent':('(i64.mul (i64.extend_i32_u ~a) (i64.const 4)) (i64.const 23)','(i64.mul (i64.extend_i32_u ~a) (i64.const 0)) (i64.const 23)'),
 'direct-output-budget':('(i64.add (i64.const ~d) (i64.extend_i32_u (local.get $result_bytes)))','(i64.add (i64.const ~d) (i64.const 16))'),
 'apply-output-budget':('(local.set $top (i32.add (local.get ~a) (local.get $result_bytes)))','(local.set $top (i32.add (local.get ~a) (i32.const 16)))'),
 'direct-copy-primary':('(memory.copy (local.get $results) (i32.add (local.get ~a) (i32.const ~d)) (i32.mul (local.get $count) (i32.const 4)))','(memory.copy (local.get $results) (i32.add (local.get ~a) (i32.const ~d)) (i32.const 4))'),
 'apply-copy-primary':('(memory.copy (local.get $results) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))','(memory.copy (local.get $results) (local.get ~a) (i32.const 4))'),
 'exception-ownership':('(write-string restore s)\n             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)','(write-string "" s)\n             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)'),
 'extent-wrap':('(i64.gt_u (i64.add (i64.extend_i32_u (local.get $top)) (local.get $wide)) (i64.extend_i32_u ~a))','(i64.gt_u (i64.extend_i32_u (i32.add (local.get $top) (i32.wrap_i64 (local.get $wide)))) (i64.extend_i32_u ~a))'),
 'result-publication':('(memory.copy (local.get $output) (local.get $results) (i32.mul (local.get $count) (i32.const 4)))','(memory.copy (local.get $output) (local.get $results) (i32.const 4))'),
 }
 return {name:one(old,new) for name,(old,new) in edits.items()}
