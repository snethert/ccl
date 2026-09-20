;; Owner-installed runtime leaf. Generated callers use the accepted internal B
;; entry. It neither allocates nor polls, and publishes at most two values.
(module
 (import "env" "memory" (memory 1 32769 shared))
 (import "env" "tcr" (global $tcr i32))
 (import "env" "call_error" (tag $error (param i32)))
 (import "hash" "run" (func $run (param i32 i32 i32 i32 i32 i32 i32 i32) (result i32)))
 (import "hash" "collect" (func $collect (param i32) (result i32)))
 (import "hash" "config" (global $config i32))
 (import "hash" "operation" (global $op i32))
 (import "hash" "scratch" (global $scratch i32))
 (import "hash" "scratch_end" (global $scratch_end i32))
 (import "hash" "result" (global $result i32))
 (global $fixed (export "fixed_calls") (mut i32) (i32.const 0))
 (global $dynamic (export "dynamic_calls") (mut i32) (i32.const 0))
 (global $direct (export "direct_calls") (mut i32) (i32.const 0))
 (func $span (param $p i32) (param $n i32)
  (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $error (i32.const 4)))))
 (func (export "entry") (param i32 i32) (result i32 i32)
  ;; This leaf is internal-only: public calls enter the generated wrapper.
  (throw $error (i32.const 4)))
 (func (export "tail_entry") (param $self i32) (param $argc i32) (param $context i32) (result i32 i32)
  (local $args i32) (local $table i32) (local $end i32) (local $dst i32) (local $n i32) (local $d i32) (local $status i32) (local $v i32) (local $old_from i32) (local $old_size i32)
  (if (i32.ne (local.get $argc) (i32.const 3)) (then (throw $error (i32.const 1))))
  (call $span (local.get $context) (i32.const 64))
  (local.set $args (i32.add (local.get $context) (i32.const 48)))
  (if (i32.or (i32.ne (local.get $args) (i32.load offset=64 (global.get $tcr))) (i32.ne (i32.add (local.get $context) (i32.const 32)) (i32.load offset=128 (global.get $tcr)))) (then (throw $error (i32.const 2))))
  (local.set $n (if (result i32) (i32.eqz (global.get $op)) (then (i32.const 2)) (else (i32.const 1))))
  (local.set $dst (i32.load offset=120 (global.get $tcr)))
  (if (i32.load offset=20 (local.get $context))
   (then
    (local.set $d (i32.load offset=28 (local.get $context))) (call $span (local.get $d) (i32.const 48))
    (if (i32.and (i32.eqz (i32.load offset=20 (local.get $d))) (i32.ne (i32.load offset=4 (local.get $d)) (i32.const -1))) (then (throw $error (i32.const 13))))
    (local.set $dst (i32.load offset=8 (local.get $d)))
    (if (i32.eqz (i32.load offset=20 (local.get $d))) (then
     (if (i32.lt_u (i32.load offset=12 (local.get $d)) (local.get $n)) (then (throw $error (i32.const 13))))))
    (if (i32.load offset=20 (local.get $d)) (then
     (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $dst)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 4))) (i64.extend_i32_u (i32.load offset=72 (global.get $tcr)))) (then (throw $error (i32.const 2)))))))
   (else
    (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $dst)) (i64.mul (i64.extend_i32_u (local.get $n)) (i64.const 4))) (i64.extend_i32_u (i32.load offset=124 (global.get $tcr)))) (then (throw $error (i32.const 3))))))
  (call $span (local.get $dst) (i32.mul (local.get $n) (i32.const 4)))
  (if (i32.eq (global.get $op) (i32.const 4)) (then
   ;; Fixture collector leaf: the continuation already roots all arguments.
   ;; Poison the retired space before returning to generated code.
   (local.set $old_from (i32.load offset=56 (global.get $tcr)))
   (local.set $old_size (i32.sub (i32.load offset=52 (global.get $tcr)) (local.get $old_from)))
   (local.set $status (call $collect (global.get $config)))
   (if (local.get $status) (then (throw $error (i32.add (i32.const 60) (local.get $status)))))
   (memory.fill (local.get $old_from) (i32.const 218) (local.get $old_size))
   (i32.store (global.get $result) (i32.const 77825))) (else
  (local.set $table (i32.load (local.get $args)))
  (if (i32.ne (i32.and (local.get $table) (i32.const 7)) (i32.const 6)) (then (throw $error (i32.const 4))))
  (call $span (i32.sub (local.get $table) (i32.const 6)) (i32.const 4))
  (local.set $end (i32.add (i32.sub (local.get $table) (i32.const 6)) (i32.and (i32.add (i32.mul (i32.shr_u (i32.load (i32.sub (local.get $table) (i32.const 6))) (i32.const 8)) (i32.const 4)) (i32.const 11)) (i32.const -8))))
  (local.set $status (call $run (local.get $table) (local.get $end) (global.get $op) (i32.load offset=4 (local.get $args)) (i32.load offset=8 (local.get $args)) (global.get $scratch) (global.get $scratch_end) (global.get $result)))
  (if (local.get $status) (then (throw $error (i32.add (i32.const 40) (local.get $status)))))
  ))
  (if (local.get $d) (then (if (i32.load offset=20 (local.get $d)) (then
   (i32.store offset=12 (local.get $d) (local.get $n))
   (i32.store offset=128 (global.get $tcr) (i32.load offset=24 (local.get $d)))))))
  (if (local.get $d) (then
   (global.set $dynamic (i32.add (global.get $dynamic) (i32.const 1)))
   (if (i32.load offset=20 (local.get $d)) (then (global.set $direct (i32.add (global.get $direct) (i32.const 1))))))
   (else (global.set $fixed (i32.add (global.get $fixed) (i32.const 1)))))
  (local.set $v (i32.load (global.get $result)))
  (i32.store (local.get $dst) (local.get $v))
  (if (i32.eq (local.get $n) (i32.const 2)) (then (i32.store offset=4 (local.get $dst) (i32.load offset=4 (global.get $result)))))
  (i32.store offset=120 (global.get $tcr) (local.get $dst))
  (i32.store offset=116 (global.get $tcr) (local.get $n))
  (local.get $v) (local.get $n)))
