;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Copyright 2026 Clozure Associates
;;;
;;; Licensed under the Apache License, Version 2.0 (the "License");
;;; you may not use this file except in compliance with the License.
;;; You may obtain a copy of the License at
;;;
;;;     http://www.apache.org/licenses/LICENSE-2.0
;;;
;;; Unless required by applicable law or agreed to in writing, software
;;; distributed under the License is distributed on an "AS IS" BASIS,
;;; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
;;; See the License for the specific language governing permissions and
;;; limitations under the License.

;;; WASM level-0 number operations.
;;; On ARM these are fast LAP paths. On WASM they are pure Lisp.

(in-package "CCL")

(defparameter *double-float-zero* 0.0d0)
(defparameter *short-float-zero* 0.0s0)


;;;; ---- Fixnum signum ----

;;; Return -1, 0, or 1 as a fixnum based on the sign of number.
(defun %fixnum-signum (number)
  (cond ((< number 0) -1)
        ((> number 0) 1)
        (t 0)))


;;;; ---- Bit counting ----

;;; Count the number of 1-bits in a fixnum (population count / logcount).
;;; Operates on the unboxed (machine-integer) representation.
(defun %ilogcount (number)
  (let* ((n number)
         (count 0))
    (declare (fixnum count))
    ;; Handle negative fixnums: logcount of negative = logcount of (lognot n)
    ;; But the ARM version just unboxes and counts, treating as unsigned.
    ;; We mirror that: work on the absolute bit pattern as unsigned.
    (loop while (not (zerop n))
          do (setq n (logand n (1- n)))  ; clear lowest set bit
             (incf count))
    count))


;;;; ---- Arithmetic shift ----

;;; Arithmetic shift: positive count = shift left, negative = shift right.
;;; Must produce a fixnum result (caller guarantees no overflow).
(defun %iash (number count)
  (ash number count))


;;;; ---- Single-float half-words ----

;;; Return the high and low 16-bit halves of a single-float's value word.
;;; Returns two values: high-16, low-16.
(defun %sfloat-hwords (sfloat)
  (let* ((word (uvref sfloat target::single-float.value-cell))
         (hi (logand #xFFFF (ash word -16)))
         (lo (logand #xFFFF word)))
    (values hi lo)))


;;;; ---- Integer length ----

;;; integer-length for fixnums.
;;; (integer-length n) = (- 32 (clz (if (>= n 0) n (lognot n))))
(defun %fixnum-intlen (number)
  (integer-length number))


;;;; ---- Float truncation to fixnum ----

;;; Truncate a double-float to a fixnum (caller guarantees result fits).
(defun %truncate-double-float->fixnum (float)
  (let* ((hi-word (uvref float target::double-float.val-high-cell))
         (lo-word (uvref float target::double-float.val-low-cell))
         (sign (if (logbitp 31 hi-word) -1 1))
         (d-exp (logand #x7FF (ash hi-word -20)))
         (sig-hi (logand hi-word #xFFFFF)))
    ;; If exponent is 0, the value is +/- 0 or denormalized (truncates to 0)
    (if (zerop d-exp)
      0
      ;; Unbiased exponent
      (let* ((unbiased (- d-exp 1023))
             ;; Full 53-bit significand with hidden bit
             (mantissa (logior (ash (logior sig-hi (ash 1 20)) 32) lo-word)))
        (if (< unbiased 0)
          0 ; |value| < 1
          (let* ((shift (- unbiased 52)))
            ;; shift > 0 means shift left, shift < 0 means shift right
            (* sign (ash mantissa shift))))))))


;;; Truncate a single-float to a fixnum (caller guarantees result fits).
(defun %truncate-short-float->fixnum (float)
  (let* ((word (uvref float target::single-float.value-cell))
         (sign (if (logbitp 31 word) -1 1))
         (s-exp (logand #xFF (ash word -23)))
         (sig (logand word #x7FFFFF)))
    (if (zerop s-exp)
      0
      (let* ((unbiased (- s-exp 127))
             ;; Full 24-bit significand with hidden bit
             (mantissa (logior sig (ash 1 23))))
        (if (< unbiased 0)
          0
          (let* ((shift (- unbiased 23)))
            (* sign (ash mantissa shift))))))))


;;;; ---- Rounding to nearest fixnum ----

;;; Round a double-float to the nearest fixnum (round-to-even).
(defun %round-nearest-double-float->fixnum (float)
  (let* ((hi-word (uvref float target::double-float.val-high-cell))
         (lo-word (uvref float target::double-float.val-low-cell))
         (sign (if (logbitp 31 hi-word) -1 1))
         (d-exp (logand #x7FF (ash hi-word -20)))
         (sig-hi (logand hi-word #xFFFFF)))
    (if (zerop d-exp)
      0
      (let* ((unbiased (- d-exp 1023))
             ;; Full 53-bit significand with hidden bit
             (mantissa (logior (ash (logior sig-hi (ash 1 20)) 32) lo-word))
             (shift (- unbiased 52)))
        (if (< unbiased -1)
          0
          (if (>= shift 0)
            ;; No fractional bits to round
            (* sign (ash mantissa shift))
            ;; Need to round: shift is negative
            (let* ((neg-shift (- shift))
                   (truncated (ash mantissa shift))
                   ;; The bit just below the rounding point
                   (half-bit (logbitp (1- neg-shift) mantissa))
                   ;; Any bits below the half bit?
                   (remainder-bits (if (> neg-shift 1)
                                     (not (zerop (logand mantissa
                                                         (1- (ash 1 (1- neg-shift))))))
                                     nil)))
              ;; Round to even: round up if half-bit set and (odd or remainder)
              (if (and half-bit
                       (or remainder-bits (oddp truncated)))
                (* sign (1+ truncated))
                (* sign truncated)))))))))


;;; Round a single-float to the nearest fixnum (round-to-even).
(defun %round-nearest-short-float->fixnum (float)
  (let* ((word (uvref float target::single-float.value-cell))
         (sign (if (logbitp 31 word) -1 1))
         (s-exp (logand #xFF (ash word -23)))
         (sig (logand word #x7FFFFF)))
    (if (zerop s-exp)
      0
      (let* ((unbiased (- s-exp 127))
             ;; Full 24-bit significand with hidden bit
             (mantissa (logior sig (ash 1 23)))
             (shift (- unbiased 23)))
        (if (< unbiased -1)
          0
          (if (>= shift 0)
            (* sign (ash mantissa shift))
            (let* ((neg-shift (- shift))
                   (truncated (ash mantissa shift))
                   (half-bit (logbitp (1- neg-shift) mantissa))
                   (remainder-bits (if (> neg-shift 1)
                                     (not (zerop (logand mantissa
                                                         (1- (ash 1 (1- neg-shift))))))
                                     nil)))
              (if (and half-bit
                       (or remainder-bits (oddp truncated)))
                (* sign (1+ truncated))
                (* sign truncated)))))))))


;;;; ---- Fixnum truncate (division) ----

;;; Return (values quotient remainder) where both are fixnums.
;;; This is (truncate dividend divisor) for fixnum arguments.
(defun %fixnum-truncate (dividend divisor)
  (if (eql divisor -1)
    ;; Special case: negation. If dividend is most-negative-fixnum,
    ;; the result overflows to a bignum — but the ARM code handles
    ;; that via *least-positive-bignum*. We let Lisp handle it.
    (values (- dividend) 0)
    (multiple-value-bind (q r) (truncate dividend divisor)
      (values q r))))


;;;; ---- Multiple-values predicate (stub) ----

;;; On ARM, checks whether the caller expects multiple values by
;;; inspecting the return address. On WASM, always return NIL.
(defun called-for-mv-p ()
  nil)


;;;; ---- GCD ----

;;; Binary GCD algorithm for positive fixnums.
;;; See <http://en.wikipedia.org/wiki/Binary_GCD_algorithm>
(defun %fixnum-gcd (n1 n2)
  (declare (fixnum n1 n2))
  ;; Handle edge cases
  (when (zerop n1) (return-from %fixnum-gcd n2))
  (when (zerop n2) (return-from %fixnum-gcd n1))
  ;; Remove common factors of 2
  (let* ((shift 0))
    (declare (fixnum shift))
    ;; Find common trailing zeros
    (loop while (and (evenp n1) (evenp n2))
          do (setq n1 (ash n1 -1))
             (setq n2 (ash n2 -1))
             (incf shift))
    ;; Remove remaining factors of 2 from n1
    (loop while (evenp n1)
          do (setq n1 (ash n1 -1)))
    ;; Main loop
    (loop
      ;; Remove factors of 2 from n2
      (loop while (evenp n2)
            do (setq n2 (ash n2 -1)))
      ;; Ensure n1 <= n2, then subtract
      (when (> n1 n2)
        (rotatef n1 n2))
      (setq n2 (- n2 n1))
      (when (zerop n2)
        (return-from %fixnum-gcd (ash n1 shift))))))


;;;; ---- PRNG (stub) ----

;;; MRG31k3p pseudo-random number generator.
;;; Full implementation requires careful unsigned 32-bit arithmetic.
;;; Stub for now.
(defun %mrg31k3p (state)
  (declare (ignore state))
  0)


;;;; ---- Complex float construction (stubs) ----

(defun %make-complex-double-float (r i result)
  (declare (ignore r i result))
  (error "~S not yet implemented on WASM" '%make-complex-double-float))

(defun %make-complex-single-float (r i result)
  (declare (ignore r i result))
  (error "~S not yet implemented on WASM" '%make-complex-single-float))

; End of wasm-numbers.lisp
