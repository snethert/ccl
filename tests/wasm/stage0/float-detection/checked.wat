;; D6 floating-point detection: checked f64 add, sub, mul, div and sqrt, a
;; checked float-to-integer conversion, and the f32 default-mode slice, with
;; no engine flags available.
;;
;; A checked operation writes the IEEE result to memory and returns a status
;; word: 0 exact, 1 overflow, 2 division-by-zero, 3 invalid, 4 underflow,
;; 5 inexact, 6 bignum path (conversion), 7 finite and not classified beyond
;; the default mode (f32 slice). NaN operands propagate as NaN with status 0;
;; invalid means a NaN produced from non-NaN operands.
;;
;; Overflow, division by zero and invalid, the three conditions U1 signals by
;; default, are decided from operand and result classification alone.
;; Underflow and inexact need an exactness witness: TwoSum for addition and
;; subtraction (exact for every finite pair), Dekker's TwoProduct for
;; multiplication with a scaled split for large operands, the residual for
;; division and the squared residual for sqrt. Tiny products and quotients are
;; witnessed on operands scaled by exact powers of two so that no partial
;; product underflows; a subnormal sqrt operand is scaled by 2^1074.
;; Tininess is decided after rounding as IEEE 754 and x86 SSE define it: a
;; result is tiny when rounding it to 53 bits with an unbounded exponent range
;; gives a magnitude below 2^-1022. That differs from testing the final result
;; only when the final result is exactly the smallest normal, so the witness
;; decides that case from the exact error.
(module
  (import "env" "memory" (memory 1 1))
  (global $INF f64 (f64.const inf))
  (global $MIN_NORMAL f64 (f64.const 0x1p-1022))
  (global $SPLIT f64 (f64.const 134217729))          ;; 2^27 + 1
  (global $BIG f64 (f64.const 0x1p996))
  (global $SCALE_DOWN f64 (f64.const 0x1p-28))
  (global $SCALE_UP f64 (f64.const 0x1p28))
  (global $S537 f64 (f64.const 0x1p537))              ;; two of these scale by 2^1074 exactly
  (global $S537_INV f64 (f64.const 0x1p-537))
  (global $WITNESS_MIN f64 (f64.const 0x1p-970))      ;; below this the plain witness's partial products could underflow
  (global $S52 f64 (f64.const 0x1p52))
  (global $QUARTER f64 (f64.const 0.25))
  (global $ONE f64 (f64.const 1))

  (func $isnan (param $x f64) (result i32) (f64.ne (local.get $x) (local.get $x)))
  (func $isinf (param $x f64) (result i32) (f64.eq (f64.abs (local.get $x)) (global.get $INF)))
  (func $iszero (param $x f64) (result i32) (f64.eq (local.get $x) (f64.const 0)))
  (func $tiny (param $x f64) (result i32) (f64.lt (f64.abs (local.get $x)) (global.get $MIN_NORMAL)))
  (func $small (param $x f64) (result i32) (f64.lt (f64.abs (local.get $x)) (global.get $WITNESS_MIN)))
  (func $up1074 (param $x f64) (result f64) (f64.mul (f64.mul (local.get $x) (global.get $S537)) (global.get $S537)))
  (func $down1074 (param $x f64) (result f64) (f64.mul (f64.mul (local.get $x) (global.get $S537_INV)) (global.get $S537_INV)))

  ;; TwoSum: s = fl(a + b); returns e with s + e = a + b exactly.
  (func $twosum_error (param $a f64) (param $b f64) (param $s f64) (result f64) (local $bb f64)
    (local.set $bb (f64.sub (local.get $s) (local.get $a)))
    (f64.add (f64.sub (local.get $a) (f64.sub (local.get $s) (local.get $bb))) (f64.sub (local.get $b) (local.get $bb))))
  ;; Dekker split of an operand whose magnitude is at most 2^996: the splitter product cannot overflow.
  (func $split_hi (param $x f64) (result f64) (local $t f64)
    (local.set $t (f64.mul (global.get $SPLIT) (local.get $x)))
    (f64.sub (local.get $t) (f64.sub (local.get $t) (local.get $x))))
  ;; TwoProduct error: p = fl(a * b); returns e with p + e = a * b exactly when no partial product underflows.
  ;; A factor above 2^996 is scaled down by 2^28 together with the product, which commutes with the
  ;; rounding of a normal product, and the error is scaled back up. Scaling the split's high part instead
  ;; can overflow when it rounds up to 2^1024 (the review's MAX * 1 counterexample).
  (func $twoproduct_error (param $a f64) (param $b f64) (param $p f64) (result f64)
    (if (f64.gt (f64.abs (local.get $a)) (global.get $BIG))
      (then (return (f64.mul (call $twoproduct_plain (f64.mul (local.get $a) (global.get $SCALE_DOWN)) (local.get $b) (f64.mul (local.get $p) (global.get $SCALE_DOWN))) (global.get $SCALE_UP)))))
    (if (f64.gt (f64.abs (local.get $b)) (global.get $BIG))
      (then (return (f64.mul (call $twoproduct_plain (local.get $a) (f64.mul (local.get $b) (global.get $SCALE_DOWN)) (f64.mul (local.get $p) (global.get $SCALE_DOWN))) (global.get $SCALE_UP)))))
    (call $twoproduct_plain (local.get $a) (local.get $b) (local.get $p)))
  (func $twoproduct_plain (param $a f64) (param $b f64) (param $p f64) (result f64)
    (local $ah f64) (local $al f64) (local $bh f64) (local $bl f64)
    (local.set $ah (call $split_hi (local.get $a))) (local.set $al (f64.sub (local.get $a) (local.get $ah)))
    (local.set $bh (call $split_hi (local.get $b))) (local.set $bl (f64.sub (local.get $b) (local.get $bh)))
    (f64.add (f64.add (f64.add (f64.sub (f64.mul (local.get $ah) (local.get $bh)) (local.get $p))
                               (f64.mul (local.get $ah) (local.get $bl)))
                      (f64.mul (local.get $al) (local.get $bh)))
             (f64.mul (local.get $al) (local.get $bl))))
  ;; Status for a finite result given whether it is exact and, for a result whose magnitude is exactly the
  ;; smallest normal, whether it is tiny after rounding: the exact value rounded to 53 bits with an unbounded
  ;; exponent range lies below 2^-1022 although the bounded rounding reached it. Every other tiny result is
  ;; subnormal or zero, so the final result decides.
  (func $status (param $r f64) (param $exact i32) (param $boundary_tiny i32) (result i32)
    (if (local.get $exact) (then (return (i32.const 0))))
    (select (i32.const 4) (i32.const 5)
      (i32.or (call $tiny (local.get $r))
              (i32.and (f64.eq (f64.abs (local.get $r)) (global.get $MIN_NORMAL)) (local.get $boundary_tiny)))))
  ;; Common classification for the infinite and NaN outcomes of a two-operand operation.
  ;; Returns -1 when the finite path must decide.
  (func $special2 (param $a f64) (param $b f64) (param $r f64) (result i32)
    (if (i32.or (call $isnan (local.get $a)) (call $isnan (local.get $b))) (then (return (i32.const 0))))
    (if (call $isnan (local.get $r)) (then (return (i32.const 3))))
    (if (call $isinf (local.get $r))
      (then (return (select (i32.const 0) (i32.const 1) (i32.or (call $isinf (local.get $a)) (call $isinf (local.get $b)))))))
    (i32.const -1))

  (func (export "add") (param $a f64) (param $b f64) (result i32) (local $r f64) (local $s i32)
    (local.set $r (f64.add (local.get $a) (local.get $b)))
    (f64.store (i32.const 0) (local.get $r))
    (local.set $s (call $special2 (local.get $a) (local.get $b) (local.get $r)))
    (if (i32.ge_s (local.get $s) (i32.const 0)) (then (return (local.get $s))))
    (call $status (local.get $r) (call $iszero (call $twosum_error (local.get $a) (local.get $b) (local.get $r))) (i32.const 0)))
  (func (export "sub") (param $a f64) (param $b f64) (result i32) (local $r f64) (local $s i32)
    (local.set $r (f64.sub (local.get $a) (local.get $b)))
    (f64.store (i32.const 0) (local.get $r))
    (local.set $s (call $special2 (local.get $a) (local.get $b) (local.get $r)))
    (if (i32.ge_s (local.get $s) (i32.const 0)) (then (return (local.get $s))))
    (call $status (local.get $r) (call $iszero (call $twosum_error (local.get $a) (f64.neg (local.get $b)) (local.get $r))) (i32.const 0)))
  (func (export "mul") (param $a f64) (param $b f64) (result i32) (local $r f64) (local $s i32) (local $as f64) (local $bs f64) (local $rs f64) (local $e f64)
    (local.set $r (f64.mul (local.get $a) (local.get $b)))
    (f64.store (i32.const 0) (local.get $r))
    (local.set $s (call $special2 (local.get $a) (local.get $b) (local.get $r)))
    (if (i32.ge_s (local.get $s) (i32.const 0)) (then (return (local.get $s))))
    (if (i32.or (call $iszero (local.get $a)) (call $iszero (local.get $b))) (then (return (i32.const 0))))
    (if (call $iszero (local.get $r)) (then (return (i32.const 4))))        ;; nonzero factors, zero product
    (if (call $small (local.get $r))
      (then
        ;; scale both factors by 2^537 (exact); the scaled product is at least 1, so no partial product underflows
        (local.set $as (f64.mul (local.get $a) (global.get $S537)))
        (local.set $bs (f64.mul (local.get $b) (global.get $S537)))
        (local.set $rs (f64.mul (local.get $as) (local.get $bs)))
        ;; e = (exact product - r) * 2^1074 exactly: rs and r * 2^1074 are within a factor of two (Sterbenz) and the
        ;; TwoProduct error is exact; e is a multiple of 2^-53 with magnitude at most 1, so the sum is exact
        (local.set $e (f64.add (f64.sub (local.get $rs) (call $up1074 (local.get $r)))
                               (call $twoproduct_error (local.get $as) (local.get $bs) (local.get $rs))))
        (return (call $status (local.get $r) (call $iszero (local.get $e))
          ;; at |r| = 2^-1022 the product is tiny after rounding iff the exact product lies more than 2^-1076 below r
          ;; in magnitude: rounding it to 53 bits then gives 2^-1022 - 2^-1075 or less; exactly 2^-1076 below is a tie
          ;; that rounds to even, 2^-1022
          (f64.lt (f64.mul (local.get $e) (f64.copysign (global.get $ONE) (local.get $r))) (f64.neg (global.get $QUARTER)))))))
    ;; a small factor cannot be split exactly; scale it up by 2^537, which commutes with the rounding of a normal product
    (if (call $small (local.get $a))
      (then (local.set $as (f64.mul (local.get $a) (global.get $S537))) (local.set $rs (f64.mul (local.get $as) (local.get $b)))
            (return (call $status (local.get $r)
              (i32.and (call $iszero (call $twoproduct_error (local.get $as) (local.get $b) (local.get $rs)))
                       (f64.eq (f64.mul (local.get $r) (global.get $S537)) (local.get $rs))) (i32.const 0)))))
    (if (call $small (local.get $b))
      (then (local.set $bs (f64.mul (local.get $b) (global.get $S537))) (local.set $rs (f64.mul (local.get $a) (local.get $bs)))
            (return (call $status (local.get $r)
              (i32.and (call $iszero (call $twoproduct_error (local.get $a) (local.get $bs) (local.get $rs)))
                       (f64.eq (f64.mul (local.get $r) (global.get $S537)) (local.get $rs))) (i32.const 0)))))
    (call $status (local.get $r) (call $iszero (call $twoproduct_error (local.get $a) (local.get $b) (local.get $r))) (i32.const 0)))
  (func (export "div") (param $a f64) (param $b f64) (result i32) (local $r f64) (local $s i32) (local $as f64) (local $bs f64) (local $rs f64) (local $p f64)
    (local.set $r (f64.div (local.get $a) (local.get $b)))
    (f64.store (i32.const 0) (local.get $r))
    (if (i32.or (call $isnan (local.get $a)) (call $isnan (local.get $b))) (then (return (i32.const 0))))
    (if (call $isnan (local.get $r)) (then (return (i32.const 3))))            ;; 0/0, inf/inf
    (if (call $iszero (local.get $b))
      (then (return (select (i32.const 0) (i32.const 2) (call $isinf (local.get $a))))))   ;; finite nonzero / 0
    (if (call $isinf (local.get $r)) (then (return (select (i32.const 0) (i32.const 1) (call $isinf (local.get $a))))))
    (if (i32.or (call $isinf (local.get $b)) (call $iszero (local.get $a))) (then (return (i32.const 0))))   ;; exact zero
    (if (call $iszero (local.get $r)) (then (return (i32.const 4))))
    (if (call $small (local.get $r))
      (then
        ;; scale the dividend up or the divisor down by 2^1074 (exact either way for a small quotient)
        (if (f64.lt (f64.abs (local.get $a)) (f64.const 0x1p-51))
          (then (local.set $as (call $up1074 (local.get $a))) (local.set $bs (local.get $b)))
          (else (local.set $as (local.get $a)) (local.set $bs (call $down1074 (local.get $b)))))
        (local.set $rs (f64.div (local.get $as) (local.get $bs)))
        (local.set $p (f64.mul (local.get $rs) (local.get $bs)))
        (return (call $status (local.get $r)
          (i32.and (call $iszero (f64.sub (f64.sub (local.get $as) (local.get $p)) (call $twoproduct_error (local.get $rs) (local.get $bs) (local.get $p))))
                   (f64.eq (call $up1074 (local.get $r)) (local.get $rs)))
          ;; at |r| = 2^-1022 the quotient is tiny after rounding iff |as| < (2^52 - 1/4) |bs|: |as| - 2^52 |bs| is exact
          ;; (Sterbenz, the scaled quotient being within half a unit of 2^52) and adding |bs| / 4 keeps the exact sign
          (f64.lt (f64.add (f64.sub (f64.abs (local.get $as)) (f64.mul (global.get $S52) (f64.abs (local.get $bs))))
                           (f64.mul (global.get $QUARTER) (f64.abs (local.get $bs))))
                  (f64.const 0))))))
    ;; a small dividend with a normal quotient: scale both operands by 2^537, which leaves the quotient unchanged
    (if (call $small (local.get $a))
      (then (local.set $as (f64.mul (local.get $a) (global.get $S537))) (local.set $bs (f64.mul (local.get $b) (global.get $S537)))
            (local.set $p (f64.mul (local.get $r) (local.get $bs)))
            (return (call $status (local.get $r)
              (call $iszero (f64.sub (f64.sub (local.get $as) (local.get $p)) (call $twoproduct_error (local.get $r) (local.get $bs) (local.get $p)))) (i32.const 0)))))
    (local.set $p (f64.mul (local.get $r) (local.get $b)))
    (call $status (local.get $r)
      (call $iszero (f64.sub (f64.sub (local.get $a) (local.get $p)) (call $twoproduct_error (local.get $r) (local.get $b) (local.get $p)))) (i32.const 0)))
  (func (export "sqrt") (param $a f64) (result i32) (local $r f64) (local $as f64) (local $rs f64) (local $p f64)
    (local.set $r (f64.sqrt (local.get $a)))
    (f64.store (i32.const 0) (local.get $r))
    (if (call $isnan (local.get $a)) (then (return (i32.const 0))))
    (if (call $isnan (local.get $r)) (then (return (i32.const 3))))            ;; negative operand
    (if (i32.or (call $isinf (local.get $r)) (call $iszero (local.get $r))) (then (return (i32.const 0))))
    (if (call $small (local.get $a))
      (then (local.set $as (call $up1074 (local.get $a))) (local.set $rs (f64.sqrt (local.get $as))))   ;; sqrt(a * 2^1074) = sqrt(a) * 2^537, and the scaling commutes with rounding
      (else (local.set $as (local.get $a)) (local.set $rs (local.get $r))))
    (local.set $p (f64.mul (local.get $rs) (local.get $rs)))
    (call $status (local.get $r)
      (call $iszero (f64.sub (f64.sub (local.get $as) (local.get $p)) (call $twoproduct_error (local.get $rs) (local.get $rs) (local.get $p)))) (i32.const 0)))

  ;; Checked conversion toward zero: status 3 for NaN or infinity, 6 when the
  ;; truncated value is outside the fixnum range and takes the bignum path,
  ;; otherwise 0 with the i32 stored. Never a trapping truncation.
  (func (export "trunc") (param $a f64) (result i32) (local $t f64)
    (if (i32.or (call $isnan (local.get $a)) (call $isinf (local.get $a))) (then (return (i32.const 3))))
    (local.set $t (f64.trunc (local.get $a)))
    (f64.store (i32.const 0) (local.get $t))
    (if (i32.or (f64.ge (local.get $t) (f64.const 0x1p29)) (f64.lt (local.get $t) (f64.const -0x1p29)))
      (then (return (i32.const 6))))
    (i32.store (i32.const 8) (i32.trunc_sat_f64_s (local.get $t)))
    (i32.const 0))

  ;; Single-float default-mode slice: overflow, division by zero and invalid
  ;; from classification; finite results report 7 (not witnessed here).
  (func $isnan32 (param $x f32) (result i32) (f32.ne (local.get $x) (local.get $x)))
  (func $isinf32 (param $x f32) (result i32) (f32.eq (f32.abs (local.get $x)) (f32.const inf)))
  (func $iszero32 (param $x f32) (result i32) (f32.eq (local.get $x) (f32.const 0)))
  (func $special32 (param $a f32) (param $b f32) (param $r f32) (result i32)
    (if (i32.or (call $isnan32 (local.get $a)) (call $isnan32 (local.get $b))) (then (return (i32.const 0))))
    (if (call $isnan32 (local.get $r)) (then (return (i32.const 3))))
    (if (call $isinf32 (local.get $r))
      (then (return (select (i32.const 0) (i32.const 1) (i32.or (call $isinf32 (local.get $a)) (call $isinf32 (local.get $b)))))))
    (i32.const 7))
  (func (export "add32") (param $a f32) (param $b f32) (result i32) (local $r f32)
    (local.set $r (f32.add (local.get $a) (local.get $b))) (f32.store (i32.const 16) (local.get $r))
    (call $special32 (local.get $a) (local.get $b) (local.get $r)))
  (func (export "mul32") (param $a f32) (param $b f32) (result i32) (local $r f32)
    (local.set $r (f32.mul (local.get $a) (local.get $b))) (f32.store (i32.const 16) (local.get $r))
    (call $special32 (local.get $a) (local.get $b) (local.get $r)))
  ;; D6 policy layer, the ARM model (decided 16 September 2026): a logical enable
  ;; mask that lives in the TCR in production (a global here), hardware-style
  ;; cumulative flags derived from the status, and the condition chosen by ARM's
  ;; priority among the enabled flags. Flag and enable bits: invalid 1,
  ;; division-by-zero 2, overflow 4, underflow 8, inexact 16. Overflow and
  ;; underflow set the inexact flag as well, as the hardware does, so an inexact
  ;; condition is signalled for them when only inexact is enabled.
  (global $mask (mut i32) (i32.const 7))                 ;; default: invalid, division by zero, overflow
  (func (export "set_mask") (param $m i32) (global.set $mask (i32.and (local.get $m) (i32.const 31))))
  (func (export "get_mask") (result i32) (global.get $mask))
  (func $flags (export "flags") (param $status i32) (result i32)
    (if (i32.eq (local.get $status) (i32.const 3)) (then (return (i32.const 1))))
    (if (i32.eq (local.get $status) (i32.const 2)) (then (return (i32.const 2))))
    (if (i32.eq (local.get $status) (i32.const 1)) (then (return (i32.const 20))))   ;; overflow sets inexact too
    (if (i32.eq (local.get $status) (i32.const 4)) (then (return (i32.const 24))))   ;; underflow sets inexact too
    (if (i32.eq (local.get $status) (i32.const 5)) (then (return (i32.const 16))))
    (i32.const 0))
  (func (export "condition") (param $status i32) (result i32) (local $e i32)
    (local.set $e (i32.and (call $flags (local.get $status)) (global.get $mask)))
    (if (i32.and (local.get $e) (i32.const 1)) (then (return (i32.const 3))))
    (if (i32.and (local.get $e) (i32.const 2)) (then (return (i32.const 2))))
    (if (i32.and (local.get $e) (i32.const 4)) (then (return (i32.const 1))))
    (if (i32.and (local.get $e) (i32.const 8)) (then (return (i32.const 4))))
    (if (i32.and (local.get $e) (i32.const 16)) (then (return (i32.const 5))))
    (i32.const 0))
  ;; Comparison: Wasm compares are quiet, so the NaN check that fcmped on ARM and
  ;; comisd on x86 perform in hardware is explicit; the ordering result is stored.
  (func (export "compare") (param $a f64) (param $b f64) (result i32)
    (i32.store (i32.const 8) (f64.lt (local.get $a) (local.get $b)))
    (select (i32.const 3) (i32.const 0) (i32.or (call $isnan (local.get $a)) (call $isnan (local.get $b)))))

  (func (export "div32") (param $a f32) (param $b f32) (result i32) (local $r f32)
    (local.set $r (f32.div (local.get $a) (local.get $b))) (f32.store (i32.const 16) (local.get $r))
    (if (i32.or (call $isnan32 (local.get $a)) (call $isnan32 (local.get $b))) (then (return (i32.const 0))))
    (if (call $isnan32 (local.get $r)) (then (return (i32.const 3))))
    (if (call $iszero32 (local.get $b)) (then (return (select (i32.const 0) (i32.const 2) (call $isinf32 (local.get $a))))))
    (if (call $isinf32 (local.get $r)) (then (return (select (i32.const 0) (i32.const 1) (call $isinf32 (local.get $a))))))
    (i32.const 7)))
