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

;;; WASM level-0 floating-point operations.
;;; On ARM these are fast LAP paths. On WASM they are pure Lisp
;;; operating on the uvector representation of float objects.
;;;
;;; Double-float layout (WASM32):
;;;   uvref 0 = pad
;;;   uvref 1 = val-low  (low 32 bits of IEEE 754 double)
;;;   uvref 2 = val-high (high 32 bits: sign[31] exponent[30:20] significand[19:0])
;;;
;;; Single-float layout (WASM32):
;;;   uvref 0 = value (32 bits: sign[31] exponent[30:23] significand[22:0])

(in-package "CCL")

(eval-when (:compile-toplevel :execute)
  (require "NUMBER-MACROS")
  (require :number-case-macro))


;;;; ---- Construction / decomposition ----

;;; Make a double-float from fixnum components.
;;; hi  = high 24 bits of mantissa (ignore implied higher bit)
;;; lo  = low 28 bits of mantissa
;;; exp = low 11 bits used as exponent
;;; sign = sign(sign) => result sign
;;; hi result word: 1 bit sign | 11 bits exp | 20 hi bits of hi arg
;;; lo result word: 4 lo bits of hi arg | 28 lo bits of lo arg
(defun %make-float-from-fixnums (float hi lo exp sign)
  (let* ((hi-raw hi)
         (lo-raw lo)
         ;; Combine: lo-result = (lo-raw) | (low 4 bits of hi-raw shifted left 28)
         (lo-result (logand #xFFFFFFFF
                            (logior lo-raw
                                    (ash (logand hi-raw #xF) 28))))
         ;; hi-result = (hi-raw >> 4), masked to 20 bits, then OR in exponent and sign
         (hi-shifted (logand #x000FFFFF (ash hi-raw -4)))
         (hi-result (logior hi-shifted
                            (ash (logand exp #x7FF) 20))))
    (when (minusp sign)
      (setq hi-result (logior hi-result #x80000000)))
    (setf (uvref float target::double-float.val-high-cell) hi-result)
    (setf (uvref float target::double-float.val-low-cell) lo-result)
    float))


;;; Make a single-float from fixnum components.
;;; sig  = significand bits (excluding hidden bit)
;;; exp  = biased exponent
;;; sign = sign determines sign bit
(defun %make-short-float-from-fixnums (float sig exp sign)
  (let* (;; Mask significand to 23 bits
         (sig-bits (logand sig #x7FFFFF))
         ;; Build the 32-bit IEEE single value
         (value (logior sig-bits
                        (ash (logand exp #xFF) 23)
                        (if (minusp sign) #x80000000 0))))
    (setf (uvref float target::single-float.value-cell) value)
    float))


;;;; ---- Integer decode of double-float ----

;;; Returns 4 values: hi (25 bits), lo (28 bits), exp, sign
;;; hi includes the implied 1 bit for normalized numbers.
(defun %integer-decode-double-float (n)
  (let* ((hi-word (uvref n target::double-float.val-high-cell))
         (lo-word (uvref n target::double-float.val-low-cell))
         ;; Extract sign
         (sign (if (logbitp 31 hi-word) -1 1))
         ;; Extract biased exponent (bits 20-30 of high word, 11 bits)
         (exp (logand #x7FF (ash hi-word -20)))
         ;; Significand high bits (bits 0-19 of high word)
         (sig-hi (logand hi-word #xFFFFF)))
    ;; If exponent is nonzero (normalized), set the implied 1 bit
    (unless (zerop exp)
      (setq sig-hi (logior sig-hi (ash 1 20))))
    ;; Pack into 25-bit hi and 28-bit lo, matching ARM layout:
    ;;   hi = (sig-hi << 4) | (lo-word >> 28)    [25 bits]
    ;;   lo = (lo-word << 4) >> (4 - fixnumshift) ... but simpler:
    ;;   lo = (lo-word & #x0FFFFFFF) as 28-bit value
    (let* ((result-hi (logior (ash sig-hi 4)
                              (logand #xF (ash lo-word -28))))
           (result-lo (logand lo-word #x0FFFFFFF)))
      (values result-hi result-lo exp sign))))


;;; Helper: build a 53-bit bignum from hi (25 bits) and lo (28 bits).
;;; big is a 2-digit bignum.  digit 0 = low 32 bits, digit 1 = high 21 bits.
(defun make-big-53 (hi lo big)
  (let* ((hi-raw hi)
         (lo-raw lo)
         ;; Combine: full = (hi-raw << 28) | lo-raw, giving 53 bits
         ;; Low 32 bits go into digit 0, top 21 bits into digit 1
         (low-32 (logand #xFFFFFFFF (logior lo-raw (ash (logand hi-raw #xF) 28))))
         (high-21 (ash hi-raw -4)))
    (setf (uvref big 0) low-32)
    (setf (uvref big 1) high-21)
    big))


;;;; ---- Significand zero counting ----

;;; Count leading zeros in the significand of a double-float.
;;; The significand occupies bits 0-19 of the high word and all of the low word.
;;; We shift out the sign+exponent (12 bits) and count leading zeros.
(defun dfloat-significand-zeros (dfloat)
  (let* ((hi-word (uvref dfloat target::double-float.val-high-cell))
         ;; Shift out sign+exponent: keep low 20 bits, shift left 12
         (hi-shifted (logand #xFFFFFFFF (ash (logand hi-word #xFFFFF) 12))))
    (if (not (zerop hi-shifted))
      (%count-leading-zeros-32 hi-shifted)
      ;; High significand is all zero; count in low word and add 20
      (let ((lo-word (uvref dfloat target::double-float.val-low-cell)))
        (+ 20 (%count-leading-zeros-32 lo-word))))))

;;; Count leading zeros in the significand of a single-float.
;;; The significand occupies bits 0-22. Shift out sign+exponent (9 bits).
(defun sfloat-significand-zeros (sfloat)
  (let* ((word (uvref sfloat target::single-float.value-cell))
         ;; Shift out sign+exponent: keep low 23 bits, shift left 9
         (shifted (logand #xFFFFFFFF (ash (logand word #x7FFFFF) 9))))
    (%count-leading-zeros-32 shifted)))

;;; Count leading zeros in a 32-bit unsigned integer.
(defun %count-leading-zeros-32 (x)
  (if (zerop x)
    32
    (let ((n 0))
      (when (zerop (logand x #xFFFF0000))
        (setq x (ash x 16))
        (setq n (+ n 16)))
      (when (zerop (logand x #xFF000000))
        (setq x (ash x 8))
        (setq n (+ n 8)))
      (when (zerop (logand x #xF0000000))
        (setq x (ash x 4))
        (setq n (+ n 4)))
      (when (zerop (logand x #xC0000000))
        (setq x (ash x 2))
        (setq n (+ n 2)))
      (when (zerop (logand x #x80000000))
        (setq n (+ n 1)))
      n)))


;;;; ---- Unary operations ----

;;; Absolute value: clear the sign bit.
(defun %%double-float-abs! (src dest)
  (setf (uvref dest target::double-float.val-high-cell)
        (logand (uvref src target::double-float.val-high-cell) #x7FFFFFFF))
  (setf (uvref dest target::double-float.val-low-cell)
        (uvref src target::double-float.val-low-cell))
  dest)

(defun %%short-float-abs! (src dest)
  (setf (uvref dest target::single-float.value-cell)
        (logand (uvref src target::single-float.value-cell) #x7FFFFFFF))
  dest)

;;; Negate: flip the sign bit.
(defun %double-float-negate! (src dest)
  (setf (uvref dest target::double-float.val-high-cell)
        (logxor (uvref src target::double-float.val-high-cell) #x80000000))
  (setf (uvref dest target::double-float.val-low-cell)
        (uvref src target::double-float.val-low-cell))
  dest)

(defun %short-float-negate! (src dest)
  (setf (uvref dest target::single-float.value-cell)
        (logxor (uvref src target::single-float.value-cell) #x80000000))
  dest)


;;;; ---- Scaling (multiply by 2^int) ----

;;; Scale a double-float by 2^int via constructing a power-of-two double
;;; and multiplying. We build a double with exponent = (int + 1023) and
;;; zero significand, then multiply.
(defun %%scale-dfloat! (float int result)
  (let* ((hi-word (uvref float target::double-float.val-high-cell))
         (lo-word (uvref float target::double-float.val-low-cell))
         ;; Extract current exponent
         (cur-exp (logand #x7FF (ash hi-word -20)))
         ;; Compute new exponent
         (new-exp (+ cur-exp int)))
    ;; Replace exponent in hi-word: clear old exponent bits, set new
    (setf (uvref result target::double-float.val-high-cell)
          (logior (logand hi-word #x800FFFFF)
                  (ash (logand new-exp #x7FF) 20)))
    (setf (uvref result target::double-float.val-low-cell) lo-word)
    result))

;;; Scale a single-float by 2^int via exponent manipulation.
(defun %%scale-sfloat! (float int result)
  (let* ((word (uvref float target::single-float.value-cell))
         ;; Extract current exponent (bits 23-30, 8 bits)
         (cur-exp (logand #xFF (ash word -23)))
         ;; Compute new exponent
         (new-exp (+ cur-exp int)))
    ;; Replace exponent: clear old, set new
    (setf (uvref result target::single-float.value-cell)
          (logior (logand word #x807FFFFF)
                  (ash (logand new-exp #xFF) 23)))
    result))


;;;; ---- Copy ----

(defun %copy-double-float (src dest)
  (setf (uvref dest target::double-float.val-high-cell)
        (uvref src target::double-float.val-high-cell))
  (setf (uvref dest target::double-float.val-low-cell)
        (uvref src target::double-float.val-low-cell))
  dest)

(defun %copy-short-float (src dest)
  (setf (uvref dest target::single-float.value-cell)
        (uvref src target::single-float.value-cell))
  dest)


;;;; ---- Exponent access ----

;;; Extract the biased exponent from a double-float (11 bits).
(defun %double-float-exp (float)
  (let* ((hi-word (uvref float target::double-float.val-high-cell)))
    ;; Shift left 1 to drop sign, then shift right 21 to isolate 11-bit exponent
    (logand #x7FF (ash hi-word -20))))

;;; Set the biased exponent of a double-float.
(defun set-%double-float-exp (float exp)
  (let* ((hi-word (uvref float target::double-float.val-high-cell))
         ;; Clear existing exponent bits (bits 20-30)
         (cleared (logand hi-word #x800FFFFF))
         ;; Set new exponent
         (new-hi (logior cleared (ash (logand exp #x7FF) 20))))
    (setf (uvref float target::double-float.val-high-cell) new-hi)
    float))

;;; Extract the biased exponent from a single-float (8 bits).
(defun %short-float-exp (float)
  (let* ((word (uvref float target::single-float.value-cell)))
    ;; Shift left 1 to drop sign, then shift right 24 to isolate 8-bit exponent
    (logand #xFF (ash word -23))))

;;; Set the biased exponent of a single-float.
(defun set-%short-float-exp (float exp)
  (let* ((word (uvref float target::single-float.value-cell))
         ;; Clear existing exponent bits (bits 23-30)
         (cleared (logand word #x807FFFFF))
         ;; Set new exponent
         (new-word (logior cleared (ash (logand exp #xFF) 23))))
    (setf (uvref float target::single-float.value-cell) new-word)
    float))


;;;; ---- Conversion ----

;;; Convert single-float to double-float by decomposing and recomposing.
(defun %short-float->double-float (src dest)
  (let* ((word (uvref src target::single-float.value-cell))
         (sign-bit (logand word #x80000000))
         (s-exp (logand #xFF (ash word -23)))
         (s-sig (logand word #x7FFFFF)))
    (cond
      ;; Zero or denormalized
      ((zerop s-exp)
       (if (zerop s-sig)
         ;; Signed zero
         (progn
           (setf (uvref dest target::double-float.val-high-cell)
                 sign-bit)
           (setf (uvref dest target::double-float.val-low-cell) 0))
         ;; Denormalized single -> normalized double
         ;; Shift significand left until hidden bit appears
         (let* ((shift 0))
           (loop while (zerop (logand s-sig (ash 1 22)))
                 do (setq s-sig (ash s-sig 1))
                    (incf shift))
           ;; Remove hidden bit
           (setq s-sig (logand s-sig #x3FFFFF))
           ;; Double exponent: 1 - 127 + 1023 - shift = 897 - shift
           (let* ((d-exp (- 897 shift))
                  ;; Expand 22-bit significand to 52-bit: shift left 30
                  ;; High 20 bits go to high word, low 2 bits << 30 go to low word
                  (d-sig-hi (ash s-sig -2))
                  (d-sig-lo (ash (logand s-sig #x3) 30)))
             (setf (uvref dest target::double-float.val-high-cell)
                   (logior sign-bit (ash d-exp 20) d-sig-hi))
             (setf (uvref dest target::double-float.val-low-cell) d-sig-lo)))))
      ;; Infinity or NaN
      ((= s-exp #xFF)
       (setf (uvref dest target::double-float.val-high-cell)
             (logior sign-bit #x7FF00000 (ash s-sig -3)))
       (setf (uvref dest target::double-float.val-low-cell)
             (logand #xFFFFFFFF (ash s-sig 29))))
      ;; Normal
      (t
       ;; Double exponent = single exponent - 127 + 1023 = s-exp + 896
       (let* ((d-exp (+ s-exp 896))
              ;; Expand 23-bit significand to 52-bit: shift left 29
              ;; Top 20 bits -> high word significand, low 3 bits << 29 -> low word
              (d-sig-hi (ash s-sig -3))
              (d-sig-lo (logand #xFFFFFFFF (ash (logand s-sig #x7) 29))))
         (setf (uvref dest target::double-float.val-high-cell)
               (logior sign-bit (ash d-exp 20) d-sig-hi))
         (setf (uvref dest target::double-float.val-low-cell) d-sig-lo)))))
  dest)

;;; Convert double-float to single-float (may lose precision).
(defun %double-float->short-float (src dest)
  (let* ((hi-word (uvref src target::double-float.val-high-cell))
         (lo-word (uvref src target::double-float.val-low-cell))
         (sign-bit (logand hi-word #x80000000))
         (d-exp (logand #x7FF (ash hi-word -20)))
         (d-sig-hi (logand hi-word #xFFFFF))
         ;; Combine to 52-bit significand, then take top 23 bits
         ;; 52-bit sig = (d-sig-hi << 32) | lo-word
         ;; Single significand = top 23 bits = (d-sig-hi << 3) | (lo-word >> 29)
         (s-sig (logior (ash d-sig-hi 3)
                        (logand #x7 (ash lo-word -29)))))
    (cond
      ;; Zero or denormalized double
      ((zerop d-exp)
       (setf (uvref dest target::single-float.value-cell)
             (logior sign-bit 0))  ; flush denorms to zero for simplicity
       dest)
      ;; Infinity or NaN
      ((= d-exp #x7FF)
       (setf (uvref dest target::single-float.value-cell)
             (logior sign-bit #x7F800000 (logand s-sig #x7FFFFF)))
       dest)
      ;; Normal
      (t
       ;; Single exponent = double exponent - 896 (= -1023 + 127)
       (let* ((s-exp (- d-exp 896)))
         (cond
           ;; Overflow -> infinity
           ((> s-exp #xFE)
            (setf (uvref dest target::single-float.value-cell)
                  (logior sign-bit #x7F800000)))
           ;; Underflow -> zero (flush to zero)
           ((<= s-exp 0)
            (setf (uvref dest target::single-float.value-cell)
                  sign-bit))
           (t
            (setf (uvref dest target::single-float.value-cell)
                  (logior sign-bit
                          (ash s-exp 23)
                          (logand s-sig #x7FFFFF))))))
       dest)))

;;; Convert fixnum to single-float.
(defun %int-to-sfloat! (int result)
  (let* ((negative (minusp int))
         (abs-val (if negative (- int) int)))
    (if (zerop abs-val)
      (setf (uvref result target::single-float.value-cell) 0)
      ;; Find the position of the highest bit
      (let* ((bit-len (integer-length abs-val))
             ;; Biased exponent: bit-len - 1 + 127
             (exp (+ (1- bit-len) 127))
             ;; Significand: remove hidden bit, keep 23 bits
             ;; Shift to align: if bit-len > 24, shift right; if < 24, shift left
             (sig (if (> bit-len 24)
                    (ash abs-val (- 24 bit-len))
                    (ash abs-val (- 24 bit-len))))
             (sig-bits (logand sig #x7FFFFF))
             (word (logior (if negative #x80000000 0)
                           (ash (logand exp #xFF) 23)
                           sig-bits)))
        (setf (uvref result target::single-float.value-cell) word)))
    result))

;;; Convert fixnum to double-float.
(defun %int-to-dfloat (int result)
  (let* ((negative (minusp int))
         (abs-val (if negative (- int) int)))
    (if (zerop abs-val)
      (progn
        (setf (uvref result target::double-float.val-high-cell) 0)
        (setf (uvref result target::double-float.val-low-cell) 0))
      ;; Find the position of the highest bit
      (let* ((bit-len (integer-length abs-val))
             ;; Biased exponent: bit-len - 1 + 1023
             (exp (+ (1- bit-len) 1023))
             ;; Significand: remove hidden bit, keep 52 bits
             ;; Shift to align: we need 53 bits total (including hidden bit)
             (sig (if (> bit-len 53)
                    (ash abs-val (- 53 bit-len))
                    (ash abs-val (- 53 bit-len))))
             ;; Remove hidden bit
             (sig-bits (logand sig (1- (ash 1 52))))
             ;; Split into high 20 and low 32
             (sig-hi (ash sig-bits -32))
             (sig-lo (logand sig-bits #xFFFFFFFF))
             (hi-word (logior (if negative #x80000000 0)
                              (ash (logand exp #x7FF) 20)
                              sig-hi)))
        (setf (uvref result target::double-float.val-high-cell) hi-word)
        (setf (uvref result target::double-float.val-low-cell) sig-lo)))
    result))


;;;; ---- FPU status/control (all stubs on WASM) ----

;;; WASM has no floating-point status/control register.
;;; These are all no-ops or return 0.

(defun %ffi-exception-status ()
  0)

(defun %get-fpscr-control ()
  0)

(defun %get-fpscr-status ()
  0)

(defun %set-fpscr-status (val)
  (declare (ignore val))
  nil)

(defun %set-fpscr-control (val)
  (declare (ignore val))
  nil)

(defun %get-fpscr ()
  0)


;;;; ---- FP exception checking (kept for API compatibility) ----

(defun %sf-check-exception-1 (operation op0 fp-status)
  (when fp-status
    (let* ((condition-name (fp-condition-name-from-fpscr-status fp-status)))
      (error (make-instance (or condition-name 'arithmetic-error)
                            :operation operation
                            :operands (list (%copy-short-float op0 (%make-sfloat))))))))

(defun %sf-check-exception-2 (operation op0 op1 fp-status)
  (when fp-status
    (let* ((condition-name (fp-condition-name-from-fpscr-status fp-status)))
      (error (make-instance (or condition-name 'arithmetic-error)
                            :operation operation
                            :operands (list (%copy-short-float op0 (%make-sfloat))
                                            (%copy-short-float op1 (%make-sfloat))))))))

(defun %df-check-exception-1 (operation op0 fp-status)
  (when fp-status
    (let* ((condition-name (fp-condition-name-from-fpscr-status fp-status)))
      (error (make-instance (or condition-name 'arithmetic-error)
                            :operation operation
                            :operands (list (%copy-double-float op0 (%make-dfloat))))))))

(defun %df-check-exception-2 (operation op0 op1 fp-status)
  (when fp-status
    (let* ((condition-name (fp-condition-name-from-fpscr-status fp-status)))
      (error (make-instance (or condition-name 'arithmetic-error)
                            :operation operation
                            :operands (list (%copy-double-float op0 (%make-dfloat))
                                            (%copy-double-float op1 (%make-dfloat))))))))


;;;; ---- FPU mode (stub) ----

(defvar *rounding-mode-alist*
  '((:nearest . 0) (:positive . 1) (:negative . 2) (:zero . 3)))

(defun get-fpu-mode (&optional (mode nil mode-p))
  (let* ((rounding-mode :nearest)
         (overflow nil)
         (underflow nil)
         (division-by-zero nil)
         (invalid nil)
         (inexact nil))
    (if mode-p
      (ecase mode
        (:rounding-mode rounding-mode)
        (:overflow overflow)
        (:underflow underflow)
        (:division-by-zero division-by-zero)
        (:invalid invalid)
        (:inexact inexact))
      `(:rounding-mode ,rounding-mode
        :overflow ,overflow
        :underflow ,underflow
        :division-by-zero ,division-by-zero
        :invalid ,invalid
        :inexact ,inexact))))

(defun set-fpu-mode (&key (rounding-mode :nearest rounding-p)
                          (overflow t overflow-p)
                          (underflow t underflow-p)
                          (division-by-zero t zero-p)
                          (invalid t invalid-p)
                          (inexact t inexact-p))
  (declare (ignore rounding-mode overflow underflow division-by-zero
                   invalid inexact
                   rounding-p overflow-p underflow-p zero-p invalid-p inexact-p))
  ;; No-op on WASM: no hardware FPU control register
  0)

(defun fp-condition-name-from-fpscr-status (status)
  (declare (ignore status))
  ;; WASM does not expose FP exception flags; return nil
  nil)


;;;; ---- Macptr-based float operations (stubs) ----

(defun %double-float-from-macptr! (ptr byte-offset dest)
  (declare (ignore ptr byte-offset))
  ;; Stub: macptr dereferencing for floats not yet supported on WASM
  dest)

(defun %single-float-ptr->double-float-ptr (single-ptr double-ptr)
  (declare (ignore single-ptr double-ptr))
  ;; Stub: macptr float conversion not yet supported on WASM
  nil)

(defun %double-float-ptr->single-float-ptr (double-ptr single-ptr)
  (declare (ignore double-ptr single-ptr))
  ;; Stub: macptr float conversion not yet supported on WASM
  nil)

(defun %set-ieee-single-float-from-double (src-double-float macptr)
  (declare (ignore src-double-float macptr))
  ;; Stub: macptr float storage not yet supported on WASM
  nil)


;;;; ---- Utility accessors ----

(defun host-single-float-from-unsigned-byte-32 (u32)
  (let* ((f (%make-sfloat)))
    (setf (uvref f target::single-float.value-cell) u32)
    f))

(defun single-float-bits (f)
  (uvref f target::single-float.value-cell))

(defun double-float-bits (f)
  (values (uvref f target::double-float.val-high-cell)
          (uvref f target::double-float.val-low-cell)))

(defun double-float-from-bits (high low)
  (let* ((f (%make-dfloat)))
    (setf (uvref f target::double-float.val-high-cell) high
          (uvref f target::double-float.val-low-cell) low)
    f))


;;;; ---- Sign extraction ----

;;; Returns T if the double-float is negative, NIL otherwise.
;;; (Matches ARM behavior: returns NIL for positive, T for negative.)
(defun %double-float-sign (float)
  (let* ((hi-word (uvref float target::double-float.val-high-cell)))
    (if (logbitp 31 hi-word) t nil)))

;;; Returns T if the single-float is negative, NIL otherwise.
(defun %short-float-sign (float)
  (let* ((word (uvref float target::single-float.value-cell)))
    (if (logbitp 31 word) t nil)))


;;;; ---- Square root (stubs) ----

(defun %single-float-sqrt! (src dest)
  (declare (ignore src dest))
  (error "~S not yet implemented on WASM" '%single-float-sqrt!))

(defun %double-float-sqrt! (src dest)
  (declare (ignore src dest))
  (error "~S not yet implemented on WASM" '%double-float-sqrt!))
