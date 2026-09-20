;; Direct Wasm implementation of the existing floating.calculate capability.
;; A miss performs no write and delegates to the full, reviewed Lisp service.
(module
 (import "env" "memory" (memory 1 32769 shared))
 (import "env" "tcr" (global $tcr i32))
 (import "env" "boundary" (global $boundary (mut i32)))
 (import "env" "eligible" (global $eligible (mut i32)))
 (import "env" "a0" (global $a0 (mut i32))) (import "env" "a1" (global $a1 (mut i32)))
 (import "env" "b0" (global $b0 (mut i32))) (import "env" "b1" (global $b1 (mut i32)))
 (import "env" "v0" (global $v0 i32)) (import "env" "v1" (global $v1 i32))
 (import "env" "t0" (global $t0 i32)) (import "env" "t1" (global $t1 i32))
 (import "env" "c0" (global $c0 i32)) (import "env" "c1" (global $c1 i32))
 (import "env" "l0" (global $l0 i32)) (import "env" "l1" (global $l1 i32))
 (import "env" "maximum" (global $maximum i32))
 (import "regions" "contains" (func $pinned (param i32 i32) (result i32)))
 (import "fallback" "calculate" (func $slow (param i32 i32 i32) (result i32)))
 (func $t (param $o i32) (result i32) (i32.load (i32.add (global.get $tcr) (local.get $o))))
 (func $inside (param $p i32) (param $n i32) (param $lo i32) (param $hi i32) (result i32)
  (i32.and (i32.ge_u (local.get $p) (local.get $lo))
   (i64.le_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $n))) (i64.extend_i32_u (local.get $hi)))))
 (func $live (result i32) (local $base i32) (local $used i32) (local $limit i32) (local $p i32) (local $n i32)
  (local.set $base (call $t (i32.const 56))) (local.set $used (call $t (i32.const 48))) (local.set $limit (call $t (i32.const 52)))
  (if (i32.eqz (i32.or
   (i32.and (i32.eq (local.get $base) (global.get $a0)) (i32.eq (local.get $limit) (global.get $a1)))
   (i32.and (i32.eq (local.get $base) (global.get $b0)) (i32.eq (local.get $limit) (global.get $b1))))) (then (return (i32.const 0))))
  (if (i32.or (i32.and (local.get $used) (i32.const 7)) (i32.eqz (call $inside (local.get $used) (i32.const 0) (local.get $base) (local.get $limit)))) (then (return (i32.const 0))))
  (if (i32.or (i32.ne (call $t (i32.const 68)) (i32.add (global.get $v0) (i32.const 8))) (i32.ne (call $t (i32.const 72)) (global.get $v1))) (then (return (i32.const 0))))
  (if (i32.or (i32.or (i32.ne (call $t (i32.const 80)) (global.get $t0)) (i32.ne (call $t (i32.const 84)) (global.get $t1)))
   (i32.eqz (call $inside (call $t (i32.const 76)) (i32.const 0) (global.get $t0) (global.get $t1)))) (then (return (i32.const 0))))
  (if (i32.or (i32.or (i32.ne (call $t (i32.const 92)) (global.get $c0)) (i32.ne (call $t (i32.const 96)) (global.get $c1)))
   (i32.eqz (call $inside (call $t (i32.const 88)) (i32.const 0) (global.get $c0) (global.get $c1)))) (then (return (i32.const 0))))
  (if (i32.gt_u (memory.size) (global.get $maximum)) (then (return (i32.const 0))))
  (if (i32.or (i32.ne (i32.load (i32.const 77824)) (i32.const 77825))
   (i32.or (i32.ne (i32.load (i32.const 77828)) (i32.const 77825)) (i32.ne (i32.load (i32.const 77832)) (i32.const 1850)))) (then (return (i32.const 0))))
  (local.set $p (call $t (i32.const 104))) (local.set $n (call $t (i32.const 108)))
  (if (i32.or (i32.and (local.get $p) (i32.const 3)) (i32.gt_u (local.get $n) (i32.const 16777215))) (then (return (i32.const 0))))
  (local.set $n (i32.mul (local.get $n) (i32.const 4)))
  (if (i32.eqz (i32.or (call $inside (local.get $p) (local.get $n) (local.get $base) (local.get $limit))
   (call $inside (local.get $p) (local.get $n) (global.get $l0) (global.get $l1)))) (then (return (i32.const 0))))
  (local.set $p (call $t (i32.const 120))) (local.set $n (call $t (i32.const 124)))
  (if (i32.lt_u (local.get $n) (local.get $p)) (then (return (i32.const 0))))
  (local.set $n (i32.sub (local.get $n) (local.get $p)))
  (i32.or (call $inside (local.get $p) (local.get $n) (global.get $v0) (global.get $v1))
   (call $inside (local.get $p) (local.get $n) (global.get $t0) (global.get $t1))))
 (func $owned (param $p i32) (param $n i32) (result i32)
  (if (call $inside (local.get $p) (local.get $n) (call $t (i32.const 56)) (call $t (i32.const 48))) (then (return (i32.const 1))))
  (call $pinned (local.get $p) (local.get $n)))
 (func $number (param $v i32) (result f64 i32) (local $p i32) (local $h i32)
  (if (i32.eqz (i32.and (local.get $v) (i32.const 3))) (then (return (f64.convert_i32_s (i32.shr_s (local.get $v) (i32.const 2))) (i32.const 0))))
  (if (i32.ne (i32.and (local.get $v) (i32.const 7)) (i32.const 6)) (then (return (f64.const 0) (i32.const -1))))
  (local.set $p (i32.sub (local.get $v) (i32.const 6)))
  (if (i32.eqz (call $owned (local.get $p) (i32.const 4))) (then (return (f64.const 0) (i32.const -1))))
  (local.set $h (i32.load (local.get $p)))
  (if (i32.and (i32.eq (local.get $h) (i32.const 271)) (call $owned (local.get $p) (i32.const 8)))
   (then (return (f64.promote_f32 (f32.load offset=4 (local.get $p))) (i32.const 32))))
  (if (i32.and (i32.eq (local.get $h) (i32.const 791)) (call $owned (local.get $p) (i32.const 16)))
   (then (return (f64.load offset=8 (local.get $p)) (i32.const 64))))
  (f64.const 0) (i32.const -1))
 (func $finite (param $x f64) (result i32) (f64.lt (f64.abs (local.get $x)) (f64.const inf)))
 (func (export "calculate") (param $op i32) (param $root i32) (param $safe i32) (result i32)
  (local $mask i32) (local $ak i32) (local $bk i32) (local $width i32) (local $heap i32) (local $size i32)
  (local $a f64) (local $b f64) (local $r f64) (local $x f32) (local $y f32) (local $yes i32)
  (block $miss
   (br_if $miss (i32.or (i32.eqz (global.get $eligible)) (global.get $boundary)))
   (br_if $miss (i32.or (i32.gt_u (local.get $op) (i32.const 11)) (i32.gt_u (local.get $safe) (i32.const 1))))
   (br_if $miss (i32.eqz (call $live)))
   (br_if $miss (i32.or (i32.and (local.get $root) (i32.const 7))
    (i32.eqz (call $inside (local.get $root) (i32.const 24) (i32.add (global.get $v0) (i32.const 8)) (global.get $v1)))))
   (br_if $miss (i32.ne (call $t (i32.const 128)) (local.get $root)))
   (br_if $miss (i32.ne (i32.load offset=4 (local.get $root)) (i32.const 4)))
   (br_if $miss (i32.or (i32.ne (i32.load offset=16 (local.get $root)) (i32.const 77825)) (i32.ne (i32.load offset=20 (local.get $root)) (i32.const 77825))))
   (local.set $mask (call $t (i32.const 200)))
   (br_if $miss (i32.or (i32.gt_u (local.get $mask) (i32.const 31)) (i32.and (local.get $safe) (i32.ne (i32.and (local.get $mask) (i32.const 24)) (i32.const 0)))))
   (call $number (i32.load offset=8 (local.get $root))) (local.set $ak) (local.set $a)
   (br_if $miss (i32.or (i32.eq (local.get $ak) (i32.const -1)) (i32.eqz (call $finite (local.get $a)))))
   (if (i32.lt_u (local.get $op) (i32.const 10)) (then
    (call $number (i32.load offset=12 (local.get $root))) (local.set $bk) (local.set $b)
    (br_if $miss (i32.or (i32.eq (local.get $bk) (i32.const -1)) (i32.eqz (call $finite (local.get $b)))))
   ))
   ;; Comparisons never round a fixnum into the other operand's single format.
   (if (i32.and (i32.ge_u (local.get $op) (i32.const 4)) (i32.le_u (local.get $op) (i32.const 9))) (then
    (local.set $yes (if (result i32) (i32.eq (local.get $op) (i32.const 4)) (then (f64.lt (local.get $a) (local.get $b))) (else
     (if (result i32) (i32.eq (local.get $op) (i32.const 5)) (then (f64.le (local.get $a) (local.get $b))) (else
     (if (result i32) (i32.eq (local.get $op) (i32.const 6)) (then (f64.eq (local.get $a) (local.get $b))) (else
     (if (result i32) (i32.eq (local.get $op) (i32.const 7)) (then (f64.ne (local.get $a) (local.get $b))) (else
     (if (result i32) (i32.eq (local.get $op) (i32.const 8)) (then (f64.ge (local.get $a) (local.get $b))) (else (f64.gt (local.get $a) (local.get $b)))))))))))))
    (i32.store offset=16 (local.get $root) (select (i32.const 77838) (i32.const 77825) (local.get $yes)))
    (return (i32.const 3072))))
   (local.set $width (if (result i32) (i32.ge_u (local.get $op) (i32.const 10))
    (then (select (i32.const 32) (i32.const 64) (i32.eq (local.get $op) (i32.const 10))))
    (else (select (i32.const 64) (i32.const 32) (i32.or (i32.eq (local.get $ak) (i32.const 64)) (i32.eq (local.get $bk) (i32.const 64)))))))
   (if (i32.ge_u (local.get $op) (i32.const 10)) (then
    (if (i32.eq (local.get $ak) (local.get $width)) (then
     ;; The existing Lisp adapter validates both objects for identity FLOAT.
     (call $number (i32.load offset=12 (local.get $root))) (local.set $bk) (local.set $b)
     (br_if $miss (i32.or (i32.eq (local.get $bk) (i32.const -1)) (i32.eqz (call $finite (local.get $b)))))
     (i32.store offset=16 (local.get $root) (i32.load offset=8 (local.get $root))) (return (i32.const 1024))))
    (local.set $r (if (result f64) (i32.eq (local.get $width) (i32.const 32)) (then (f64.promote_f32 (f32.demote_f64 (local.get $a)))) (else (local.get $a))))
   ) (else
    (br_if $miss (i32.eqz (i32.or (local.get $ak) (local.get $bk))))
    (if (i32.eq (local.get $width) (i32.const 32)) (then
     (local.set $x (f32.demote_f64 (local.get $a))) (local.set $y (f32.demote_f64 (local.get $b)))
     (local.set $r (f64.promote_f32 (if (result f32) (i32.eq (local.get $op) (i32.const 0)) (then (f32.add (local.get $x) (local.get $y))) (else
      (if (result f32) (i32.eq (local.get $op) (i32.const 1)) (then (f32.sub (local.get $x) (local.get $y))) (else
      (if (result f32) (i32.eq (local.get $op) (i32.const 2)) (then (f32.mul (local.get $x) (local.get $y))) (else (f32.div (local.get $x) (local.get $y))))))))))
    ) (else
     (local.set $r (if (result f64) (i32.eq (local.get $op) (i32.const 0)) (then (f64.add (local.get $a) (local.get $b))) (else
      (if (result f64) (i32.eq (local.get $op) (i32.const 1)) (then (f64.sub (local.get $a) (local.get $b))) (else
      (if (result f64) (i32.eq (local.get $op) (i32.const 2)) (then (f64.mul (local.get $a) (local.get $b))) (else (f64.div (local.get $a) (local.get $b)))))))))
    ))
   ))
   (br_if $miss (i32.eqz (call $finite (local.get $r))))
   (local.set $size (select (i32.const 8) (i32.const 16) (i32.eq (local.get $width) (i32.const 32))))
   (local.set $heap (call $t (i32.const 48)))
   (br_if $miss (i32.eqz (call $inside (local.get $heap) (local.get $size) (call $t (i32.const 56)) (call $t (i32.const 52)))))
   ;; No call or safepoint from here through publication; all operands stay rooted.
   (if (i32.eq (local.get $width) (i32.const 32)) (then
    (i32.store (local.get $heap) (i32.const 271)) (f32.store offset=4 (local.get $heap) (f32.demote_f64 (local.get $r)))) (else
    (i32.store (local.get $heap) (i32.const 791)) (i32.store offset=4 (local.get $heap) (i32.const 0)) (f64.store offset=8 (local.get $heap) (local.get $r))))
   (i32.store offset=48 (global.get $tcr) (i32.add (local.get $heap) (local.get $size)))
   (i32.store offset=16 (local.get $root) (i32.add (local.get $heap) (i32.const 6)))
   (return (select (i32.const 1024) (i32.const 3072) (i32.ge_u (local.get $op) (i32.const 10))))
  )
  (call $slow (local.get $op) (local.get $root) (local.get $safe)))
)
