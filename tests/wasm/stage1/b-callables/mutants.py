def mutations(source):
 def change(old,new,count=1):
  assert source.count(old)==count,(old,source.count(old));return source.replace(old,new)
 edits={
 'symbol-cell':('(i32.load offset=12 (call $object_base','(i32.load offset=8 (call $object_base'),
 'object-header':('(i32.ne (i32.load (local.get $p)) (local.get $header))','(i32.and (i32.const 0) (i32.ne (i32.load (local.get $p)) (local.get $header)))'),
 'object-span':('(i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))','(i32.and (i32.const 0) (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))))'),
 'code-range':('(i32.ge_u (local.get $id) (local.get $cap))','(i32.and (i32.const 0) (i32.ge_u (local.get $id) (local.get $cap)))'),
 'version':('(i32.ne (i32.load offset=12 (local.get $p)) (i32.load offset=4 (local.get $row)))','(i32.const 0)'),
 'version-encoding':('(i32.or (i32.and (local.get $version) (i32.const 3)) (i32.le_s (local.get $version) (i32.const 0)))','(i32.const 0)'),
 'signature':('(i32.ne (i32.load offset=8 (local.get $row)) (i32.const 17))','(i32.const 0)'),
 'role':('(i32.ne (i32.load offset=12 (local.get $row)) (i32.const 23))','(i32.const 0)'),
 'slot-range':('(i32.ge_u (local.get $slot) (table.size))','(i32.const 0)'),
 'null-slot':('(ref.is_null (table.get (local.get $slot)))','(i32.const 0)'),
 'registry-prefix':('(i32.ne (i32.load offset=4 (global.get $code_registry)) (i32.const 1))','(i32.const 0)'),
 'function-value':('(ccl::%function (b-wat "(call $function_value ~a)"', '(ccl::%function (b-wat "~a"'),
 'apply-self':('(local.get ~a) (local.get $dispatch_slot))" base base base total)','(local.get ~a) (local.get $dispatch_slot))" base evaluated base total)'),
 'exception-ownership':('(write-string restore s)\n             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)','(write-string "" s)\n             (write-string (b-store wasm32::tcr.mv_count "(local.get $old_count)") s)'),
 }
 result={name:change(*pair) for name,pair in edits.items()}
 tag='(i32.ne (i32.and (local.get $node) (i32.const 7)) (i32.const 6))'
 result['object-tag']=change(tag,'(i32.and (i32.const 0) '+tag+')',2)
 # Preserve the incoming symbol in the frame, despite resolving its slot.
 part='(i32.store offset=8 (local.get ~a) (local.get $dispatch_self))'
 result['resolved-self']=change(part,'(i32.store offset=8 (local.get ~a) (i32.or (i32.const 196614) (i32.and (local.get $dispatch_self) (i32.const 0))))',2)
 return result
