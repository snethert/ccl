"""Single-site semantic faults in the actual compiler proposal."""
def variants(source,replace):
 faults=[
 ('missing-copy','(memory.copy (i32.add (local.get $p) (i32.const 4)) (local.get $base) (i32.mul (local.get $cap) (i32.const 4)))','(memory.fill (i32.add (local.get $p) (i32.const 4)) (i32.const 0) (i32.mul (local.get $cap) (i32.const 4)))','v_nested'),
 ('wrong-empty-marker','(i32.const 243))\n   (local.set $i','(i32.const 77825))\n   (local.set $i','v_bound'),
 ('unpublished-capacity','(i32.store offset=108 (global.get $tcr) (local.get $newcap))','(i32.store offset=108 (global.get $tcr) (local.get $cap))','v_bound'),
 ('tcr-index-clobber','(i32.store offset=108 (global.get $tcr) (local.get $newcap))','(i32.store offset=108 (global.get $tcr) (local.get $newcap)) (i32.store (global.get $tcr) (local.get $index))','v_bound'),
 ('global-only-read','(call $special_read_lisp ~a (local.get $top))\" symbol','(i32.load offset=2 ~a)\" symbol','v_bound'),
 ('global-only-set','(i32.store (call $special_location ~a) ~a) ~a\" symbol symbol value value','(i32.store offset=2 ~a ~a) ~a\" symbol symbol value value','v_bound'),
 ('wrong-restore-location','(local.set $slot (call $dynamic_slot (i32.load offset=16 (local.get $p)))))','__UNUSED__','v_bound'),
 ('constant-mutation','(i32.and (i32.load offset=14 ~a) (i32.const 8))','(i32.and (i32.load offset=14 ~a) (i32.const 0))','v_constant_set'),
 ('missing-unbound-check','(i32.eq (local.get $value) (i32.const 51)) (then (call $implicit_error_details','(i32.eq (local.get $value) (i32.const 55)) (then (call $implicit_error_details','v_unbound'),
 ('index-is-tcr-identity','(local.set $index (i32.load offset=22 (local.get $symbol)))','(local.set $index (i32.load (global.get $tcr)))','v_bound'),
 ('lost-allocation-limit','(i64.gt_u (local.get $end) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr))))','(i64.gt_u (local.get $end) (i64.const 4294967296))',None),
 ('early-publication','(local.set $p (i32.load offset=48 (global.get $tcr)))\n  (local.set $end','(local.set $p (i32.load offset=48 (global.get $tcr))) (i32.store offset=108 (global.get $tcr) (local.get $newcap))\n  (local.set $end',None),
 ]
 for name,old,new,focus in faults:
  if name=='wrong-restore-location':
   old='(local.set $slot (call $dynamic_slot (i32.load offset=16 (local.get $p)))))'
   old=old[:-1]
   new='(local.set $slot (i32.add (i32.const 610000) (i32.load offset=4 (local.get $p))))'
  yield name,replace(source,old,new),focus
