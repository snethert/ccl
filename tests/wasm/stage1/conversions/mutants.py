def mutations(source):
 prefix,body=source.split(';;; Typed internal primitives.',1)
 def one(text,old,new):
  assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)
 edits={
 'box-range':('(i32.gt_s ~a (i32.const 536870911))','(i32.gt_s ~a (i32.const 536870912))'),
 'box-shift':('(format s "(i32.shl ~a (i32.const 2))" a))\n          (%unbox-fixnum','(format s "(i32.shl ~a (i32.const 1))" a))\n          (%unbox-fixnum'),
 'sign-extension':('(i32.shr_s ~a (i32.const 2))','(i32.shr_u ~a (i32.const 2))'),
 'unsigned-address':('(i32.gt_u ~a (i32.const 536870911))','(i32.gt_s ~a (i32.const 536870911))'),
 'pointer-alignment':('(check (format nil "(i32.and ~a (i32.const 7))" a) 3)','(check (format nil "(i32.and ~a (i32.const 3))" a) 3)'),
 'pointer-tag':('(format s "(i32.add ~a (i32.const 6))" a)','(format s "(i32.add ~a (i32.const 1))" a)'),
 'negative-offset':('(i32.sub ~a (i32.const 6))','(i32.sub ~a (i32.const 4))'),
 'high-bit':('(i64.extend_i32_u ~a) (i64.extend_i32_s ~a)','(i64.extend_i32_s ~a) (i64.extend_i32_s ~a)'),
 'address-overflow':('(check "(i64.gt_u (local.get $wide) (i64.const 4294967295))" 4)\n           (write-string "(i32.wrap_i64 (local.get $wide))" s))\n          (%array-bytes','(check "(i64.gt_u (local.get $wide) (i64.const 4294967296))" 4)\n           (write-string "(i32.wrap_i64 (local.get $wide))" s))\n          (%array-bytes'),
 'exclusive-array-limit':('(i32.ge_u ~a (i32.const 16777216))','(i32.gt_u ~a (i32.const 16777216))'),
 'array-overflow':('(i64.mul (i64.extend_i32_u ~a) (i64.extend_i32_u ~a))','(i64.extend_i32_u (i32.mul ~a ~a))'),
 'issuance-store':('(i32.store offset=4 ~a (i32.add (local.get $scratch) (i32.const 1)))','(drop ~a)'),
 'unissued-id':('(i32.ge_u (local.get $scratch) ~a)','(i32.gt_u (local.get $scratch) ~a)'),
 'double-id-shift':('(%code-index (format s "(i32.shr_u ~a (i32.const 2))" a))','(%code-index (format s "(i32.shr_u ~a (i32.const 4))" a))'),
 'slot-kind':('(i32.ne ~a (i32.const 3))','(i32.ne ~a (i32.const 2))'),
 'slot-capacity':('(i32.ge_u ~a ~a)" a (word e 0)','(i32.gt_u ~a ~a)" a (word e 0)'),
 'slot-reserved':('(i32.lt_u ~a ~a)" a (word e 4)','(i32.lt_u ~a (i32.and ~a (i32.const 0)))" a (word e 4)'),
 'slot-signature':('(i32.or (i32.eqz ~a) (i32.ne ~a ~a))" c','(i32.or (i32.eqz ~a) (i32.ne (i32.and ~a (i32.const 0)) (i32.and ~a (i32.const 0))))" c'),
 'slot-role':('(i32.or (i32.eqz ~a) (i32.ne ~a ~a))" d','(i32.or (i32.eqz ~a) (i32.eq ~a ~a))" d'),
 }
 result={name:prefix+';;; Typed internal primitives.'+one(body,old,new) for name,(old,new) in edits.items()}
 result['temporary-alias']=one(source,'(format nil "$tmp~d" *temporary-count*)','(format nil "$tmp~d" 0)')
 return result
