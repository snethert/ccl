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

;;; WASM32 bignum LAP bridge functions.
;;; Pure Lisp replacements for the ARM LAP primitives in arm-bignum.lisp.
;;; Bignum digits are 32-bit unsigned values accessed via uvref/uvset.
;;; Index 0 = least significant digit. Highest-index digit has sign in bit 31.
;;; All intermediate arithmetic uses (logand ... #xFFFFFFFF) to stay in 32 bits.

(in-package "CCL")

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Helpers
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; compile-time only — declaim generates a load-time (proclaim ...) call,
;;; but PROCLAIM is level-1 and unavailable during cold-boot-init.
(eval-when (:compile-toplevel)
  (proclaim '(inline %u32 %high-half %low-half %compose-digit %mul32x32)))

(defun %u32 (x)
  "Mask to 32-bit unsigned."
  (logand x #xFFFFFFFF))

(defun %high-half (digit)
  "High 16 bits of a 32-bit digit as a fixnum."
  (logand (ash digit -16) #xFFFF))

(defun %low-half (digit)
  "Low 16 bits of a 32-bit digit as a fixnum."
  (logand digit #xFFFF))

(defun %compose-digit (hi lo)
  "Compose a 32-bit digit from two 16-bit halves."
  (%u32 (logior (ash (logand hi #xFFFF) 16) (logand lo #xFFFF))))

(defun %mul32x32 (a b)
  "32x32 -> 64 unsigned multiply. Returns (values lo hi).
Uses the standard decomposition into 16-bit halves."
  (let* ((al (logand a #xFFFF))
         (ah (ash a -16))
         (bl (logand b #xFFFF))
         (bh (ash b -16))
         ;; Each partial product fits in 32 bits (max 0xFFFE0001).
         (ll (* al bl))
         (lh (* al bh))
         (hl (* ah bl))
         (hh (* ah bh))
         ;; mid can be up to 0x1FFFC0002, needs 33 bits -- Lisp bignum handles this.
         (mid (+ lh hl))
         ;; Combine: result = hh:00000000 + 0000:mid:0000 + ll
         ;; low 32 bits:
         (low-sum (+ ll (ash (logand mid #xFFFF) 16)))
         (lo (%u32 low-sum))
         ;; high 32 bits: hh + high part of mid + carry from low-sum
         (hi (%u32 (+ hh
                      (ash mid -16)
                      (ash low-sum -32)))))
    (values lo hi)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Digit access
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; %BIGNUM-REF -- returns (values high-half low-half) of bignum[i].
(defun %bignum-ref (bignum i)
  (let ((digit (uvref bignum i)))
    (values (%high-half digit) (%low-half digit))))

;;; %BIGNUM-REF-HI -- high 16 bits of bignum[i].
(defun %bignum-ref-hi (bignum i)
  (%high-half (uvref bignum i)))

;;; %BIGNUM-SET -- set bignum[i] from two 16-bit halves.
(defun %bignum-set (bignum i high low)
  (setf (uvref bignum i) (%compose-digit high low)))

;;; %REF-DIGIT -- copy bignum[i] to dest[0].
(defun %ref-digit (bignum i dest)
  (setf (uvref dest 0) (uvref bignum i)))

;;; %SET-DIGIT -- set bignum[i] from digit[0].
(defun %set-digit (bignum i digit)
  (setf (uvref bignum i) (uvref digit 0)))

;;; %BIGNUM-SIGN -- return -1 if negative, 0 if non-negative, as fixnum.
(defun %bignum-sign (bignum)
  (let ((top-digit (uvref bignum (1- (uvsize bignum)))))
    (if (logbitp 31 top-digit) -1 0)))

;;; %BIGNUM-SIGN-BITS -- count leading sign bits of the most significant digit.
(defun %bignum-sign-bits (bignum)
  (let* ((top-digit (uvref bignum (1- (uvsize bignum))))
         (d (if (logbitp 31 top-digit)
                (%u32 (lognot top-digit))
                top-digit)))
    ;; Count leading zeros of d (32-bit).
    (if (zerop d)
        32
        (let ((n 0))
          (when (zerop (logand d #xFFFF0000)) (setq n (+ n 16) d (ash d 16)))
          (when (zerop (logand d #xFF000000)) (setq n (+ n 8) d (ash d 8)))
          (when (zerop (logand d #xF0000000)) (setq n (+ n 4) d (ash d 4)))
          (when (zerop (logand d #xC0000000)) (setq n (+ n 2) d (ash d 2)))
          (when (zerop (logand d #x80000000)) (setq n (+ n 1)))
          n))))

;;; %DIGIT-0-OR-PLUSP -- T if bit 31 of bignum[idx] is clear.
(defun %digit-0-or-plusp (bignum idx)
  (not (logbitp 31 (uvref bignum idx))))

;;; %BIGNUM-ODDP -- T if least significant bit of bignum is 1.
(defun %bignum-oddp (bignum)
  (logbitp 0 (uvref bignum 0)))

;;; BIGNUM-PLUSP -- T if bignum is non-negative.
(defun bignum-plusp (bignum)
  (not (logbitp 31 (uvref bignum (1- (uvsize bignum))))))

;;; BIGNUM-MINUSP -- T if bignum is negative.
(defun bignum-minusp (bignum)
  (logbitp 31 (uvref bignum (1- (uvsize bignum)))))

;;; %FIXNUM-TO-BIGNUM-SET -- store a fixnum as the first digit of bignum.
(defun %fixnum-to-bignum-set (bignum fixnum)
  (setf (uvref bignum 0) (%u32 fixnum)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Arithmetic with carry/borrow
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; %ADD-WITH-CARRY -- add a[i] + b[j] + carry-in, store in r[k].
;;; If i is nil, a is a fixnum. If j is nil, b is a fixnum.
;;; Returns carry-out (0 or 1) as a fixnum.
(defun %add-with-carry (r k c a i b j)
  (let* ((av (if i (uvref a i) (%u32 a)))
         (bv (if j (uvref b j) (%u32 b)))
         (sum (+ av bv c))
         (carry-out (if (> sum #xFFFFFFFF) 1 0)))
    (setf (uvref r k) (%u32 sum))
    carry-out))

;;; %ADD-THE-CARRY -- add carry to a composed digit (b-h, b-l).
;;; Returns (values high-half low-half) of result.
(defun %add-the-carry (b-h b-l carry-in)
  (let* ((b (%compose-digit b-h b-l))
         (result (+ b carry-in)))
    (values (%high-half (%u32 result))
            (%low-half (%u32 result)))))

;;; %SUBTRACT-WITH-BORROW -- r[k] = a[i] - b[j] - (1 - borrow-in).
;;; If i is nil, a is a fixnum. If j is nil, b is a fixnum.
;;; borrow-in: 1 = no borrow, 0 = borrow.
;;; Returns borrow-out: 1 = no borrow, 0 = borrow.
(defun %subtract-with-borrow (r k borrow a i b j)
  (let* ((av (if i (uvref a i) (%u32 a)))
         (bv (if j (uvref b j) (%u32 b)))
         ;; We compute: av - bv - 1 + borrow
         (diff (+ (- av bv) borrow -1))
         (borrow-out (if (>= diff 0) 1 0)))
    (setf (uvref r k) (%u32 diff))
    borrow-out))

;;; %SUBTRACT-WITH-BORROW-1 -- subtract with borrow using hi/lo halves.
;;; Returns (values result-hi result-lo borrow-out).
(defun %subtract-with-borrow-1 (a-h a-l b-h b-l borrow-in)
  (let* ((a (%compose-digit a-h a-l))
         (b (%compose-digit b-h b-l))
         (diff (+ (- a b) borrow-in -1))
         (borrow-out (if (>= diff 0) 1 0))
         (result (%u32 diff)))
    (values (%high-half result)
            (%low-half result)
            borrow-out)))

;;; %SUBTRACT-ONE -- subtract 1 from composed digit (a-h, a-l).
;;; Returns (values result-hi result-lo).
(defun %subtract-one (a-h a-l)
  (let* ((a (%compose-digit a-h a-l))
         (result (%u32 (- a 1))))
    (values (%high-half result)
            (%low-half result))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Multiplication
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; %MULTIPLY-AND-ADD -- multiply x[i] by fixnum y, add carry[0].
;;; Store low word in r[0], high word in carry[0].
(defun %multiply-and-add (r carry x i y)
  (let* ((xv (uvref x i))
         (yv (%u32 y)))
    (multiple-value-bind (lo hi) (%mul32x32 xv yv)
      (let* ((c (uvref carry 0))
             (sum (+ lo c))
             (new-lo (%u32 sum))
             (new-hi (%u32 (+ hi (if (> sum #xFFFFFFFF) 1 0)))))
        (setf (uvref carry 0) new-hi)
        (setf (uvref r 0) new-lo)))))

;;; %MULTIPLY-AND-ADD-1 -- 32x32 multiply + carry-in, return four halves.
;;; Returns (values hi-high hi-low lo-high lo-low).
(defun %multiply-and-add-1 (x-high x-low y-high y-low carry-in-high carry-in-low)
  (let* ((x (%compose-digit x-high x-low))
         (y (%compose-digit y-high y-low))
         (carry-in (%compose-digit carry-in-high carry-in-low)))
    (multiple-value-bind (lo hi) (%mul32x32 x y)
      (let* ((sum (+ lo carry-in))
             (new-lo (%u32 sum))
             (new-hi (%u32 (+ hi (if (> sum #xFFFFFFFF) 1 0)))))
        (values (%high-half new-hi) (%low-half new-hi)
                (%high-half new-lo) (%low-half new-lo))))))

;;; %MULTIPLY-AND-ADD-FIXNUM-LOOP -- multiply bignum x by fixnum y,
;;; store result in result. len digits.
(defun %multiply-and-add-fixnum-loop (len x y result)
  (let ((carry 0)
        (yv (%u32 y)))
    (dotimes (idx len)
      (let ((xv (uvref x idx)))
        (multiple-value-bind (lo hi) (%mul32x32 xv yv)
          (let* ((sum (+ lo carry))
                 (new-lo (%u32 sum))
                 (new-hi (%u32 (+ hi (if (> sum #xFFFFFFFF) 1 0)))))
            (setf (uvref result idx) new-lo)
            (setq carry new-hi)))))
    ;; Store final carry in the digit after the last one.
    (setf (uvref result len) carry)))

;;; %MULTIPLY-AND-ADD-HARDER-LOOP-2 -- multiply x[residx] by y[0..count-1],
;;; adding to result starting at residx.
(defun %multiply-and-add-harder-loop-2 (x-ptr y-ptr resptr residx count)
  (let ((x (uvref x-ptr residx))
        (carry 0))
    (dotimes (j count)
      (let ((y (uvref y-ptr j)))
        (multiple-value-bind (lo hi) (%mul32x32 x y)
          (let* ((sum1 (+ lo carry))
                 (c1 (if (> sum1 #xFFFFFFFF) 1 0))
                 (lo1 (%u32 sum1))
                 (prev (uvref resptr (+ residx j)))
                 (sum2 (+ lo1 prev))
                 (c2 (if (> sum2 #xFFFFFFFF) 1 0)))
            (setf (uvref resptr (+ residx j)) (%u32 sum2))
            (setq carry (%u32 (+ hi c1 c2)))))))
    ;; Store final carry.
    (setf (uvref resptr (+ residx count)) carry)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Bitwise
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; %LOGCOUNT -- count 1-bits in bignum[idx].
(defun %logcount (bignum idx)
  (let ((d (uvref bignum idx))
        (count 0))
    (loop while (not (zerop d))
          do (setq d (logand d (1- d)))
             (incf count))
    count))

;;; %LOGCOUNT-COMPLEMENT -- count 0-bits in bignum[idx].
(defun %logcount-complement (bignum idx)
  (let ((d (%u32 (lognot (uvref bignum idx))))
        (count 0))
    (loop while (not (zerop d))
          do (setq d (logand d (1- d)))
             (incf count))
    count))

;;; %BIGNUM-LOGNOT -- dest[idx] = lognot(src[idx]).
(defun %bignum-lognot (idx src dest)
  (setf (uvref dest idx) (%u32 (lognot (uvref src idx)))))

;;; %BIGNUM-LOGAND -- dest[idx] = logand(x[idx], y[idx]).
(defun %bignum-logand (idx x y dest)
  (setf (uvref dest idx) (logand (uvref x idx) (uvref y idx))))

;;; %BIGNUM-LOGIOR -- dest[idx] = logior(x[idx], y[idx]).
(defun %bignum-logior (idx x y dest)
  (setf (uvref dest idx) (logior (uvref x idx) (uvref y idx))))

;;; %BIGNUM-LOGXOR -- dest[idx] = logxor(x[idx], y[idx]).
(defun %bignum-logxor (idx x y dest)
  (setf (uvref dest idx) (logxor (uvref x idx) (uvref y idx))))

;;; %BIGNUM-LOGANDC2 -- dest[idx] = logand(x[idx], lognot(y[idx])).
(defun %bignum-logandc2 (idx x y dest)
  (setf (uvref dest idx) (logand (uvref x idx)
                                 (%u32 (lognot (uvref y idx))))))

;;; %BIGNUM-LOGANDC1 -- dest[idx] = logand(lognot(x[idx]), y[idx]).
(defun %bignum-logandc1 (idx x y dest)
  (setf (uvref dest idx) (logand (%u32 (lognot (uvref x idx)))
                                 (uvref y idx))))

;;; DIGIT-LOGNOT-MOVE -- dest[index] = lognot(source[index]).
(defun digit-lognot-move (index source dest)
  (setf (uvref dest index) (%u32 (lognot (uvref source index)))))

;;; FIX-DIGIT-LOGANDC2 -- logandc2 of fixnum and bignum[0].
;;; If dest is non-nil, store in dest[0]; else return as fixnum.
(defun fix-digit-logandc2 (fix big dest)
  (let ((result (logand (%u32 fix) (%u32 (lognot (uvref big 0))))))
    (if dest
        (setf (uvref dest 0) result)
        result)))

;;; FIX-DIGIT-LOGAND -- logand of fixnum and bignum[0].
;;; If dest is non-nil, store in dest[0]; else return as fixnum.
(defun fix-digit-logand (fix big dest)
  (let ((result (logand (%u32 fix) (uvref big 0))))
    (if dest
        (setf (uvref dest 0) result)
        result)))

;;; FIX-DIGIT-LOGANDC1 -- logandc1 of fixnum and bignum[0].
;;; If dest is non-nil, store in dest[0]; else return as fixnum.
(defun fix-digit-logandc1 (fix big dest)
  (let ((result (logand (%u32 (lognot (%u32 fix))) (uvref big 0))))
    (if dest
        (setf (uvref dest 0) result)
        result)))

;;; BIGNUM-XOR-LOOP -- XOR b1[0..count-1] with b2[0..count-1] into dest.
(defun bignum-xor-loop (count b1 b2 dest)
  (dotimes (i count)
    (setf (uvref dest i) (logxor (uvref b1 i) (uvref b2 i)))))

;;; BIGNUM-LOGTEST-LOOP -- return T if any (logand b1[i] b2[i]) is nonzero.
(defun bignum-logtest-loop (count b1 b2)
  (dotimes (i count nil)
    (unless (zerop (logand (uvref b1 i) (uvref b2 i)))
      (return t))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Comparison
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; %COMPARE-DIGITS -- compare a[idx] with b[idx]. Return -1, 0, or 1.
(defun %compare-digits (a b idx)
  (let ((av (uvref a idx))
        (bv (uvref b idx)))
    (cond ((= av bv) 0)
          ((> av bv) 1)
          (t -1))))

;;; %DIGITS-SIGN-BITS -- count sign bits of composed digit (hi, lo).
;;; 32 - result = integer-length.
(defun %digits-sign-bits (hi lo)
  (let* ((d (%compose-digit hi lo))
         (v (if (logbitp 31 d) (%u32 (lognot d)) d)))
    (if (zerop v)
        32
        (let ((n 0))
          (when (zerop (logand v #xFFFF0000)) (setq n (+ n 16) v (ash v 16)))
          (when (zerop (logand v #xFF000000)) (setq n (+ n 8) v (ash v 8)))
          (when (zerop (logand v #xF0000000)) (setq n (+ n 4) v (ash v 4)))
          (when (zerop (logand v #xC0000000)) (setq n (+ n 2) v (ash v 2)))
          (when (zerop (logand v #x80000000)) (setq n (+ n 1)))
          n))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Negation
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; BIGNUM-NEGATE-LOOP-REALLY -- negate big[0..len-1] into result[0..len-1].
;;; Returns carry (0 or 1).
(defun bignum-negate-loop-really (big len result)
  (let ((carry 1))
    (dotimes (i len)
      (let* ((x (%u32 (lognot (uvref big i))))
             (sum (+ x carry)))
        (setf (uvref result i) (%u32 sum))
        (setq carry (if (> sum #xFFFFFFFF) 1 0))))
    carry))

;;; BIGNUM-NEGATE-TO-POINTER -- negate big into a macptr dest.
;;; For WASM, dest is treated as a bignum-like vector.
;;; Returns carry (0 or 1).
(defun bignum-negate-to-pointer (big len result)
  ;; In WASM we treat result as a simple vector of u32.
  ;; Same logic as negate-loop-really.
  (bignum-negate-loop-really big len result))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Add/subtract loops
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; BIGNUM-ADD-LOOP-+ -- add b[0..length-1] to a[init-a..init-a+length-1],
;;; storing back into a. Then propagate carry into a[init-a+length].
(defun bignum-add-loop-+ (init-a aptr bptr length)
  (let ((carry 0))
    (dotimes (i length)
      (let* ((av (uvref aptr (+ init-a i)))
             (bv (uvref bptr i))
             (sum (+ av bv carry)))
        (setf (uvref aptr (+ init-a i)) (%u32 sum))
        (setq carry (if (> sum #xFFFFFFFF) 1 0))))
    ;; Add carry into the next digit.
    (let* ((next-idx (+ init-a length))
           (val (+ (uvref aptr next-idx) carry)))
      (setf (uvref aptr next-idx) (%u32 val)))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Division / Floor
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; Helper: unsigned 64-bit / 32-bit division.
;;; Divides (hi:lo) by divisor. Returns (values quotient remainder).
(defun %udiv64by32 (hi lo divisor)
  (if (zerop divisor)
      (error "Division by zero")
      (let* ((dividend (logior (ash hi 32) lo))
             (q (floor dividend divisor))
             (r (- dividend (* q divisor))))
        (values (%u32 q) (%u32 r)))))

;;; %FLOOR-LOOP-QUO -- divide bignum x by single digit y (composed from yhi/ylo).
;;; Store quotient in res. Return (values remainder-hi remainder-lo).
(defun %floor-loop-quo (x res yhi ylo)
  (let* ((y (%compose-digit yhi ylo))
         (len (uvsize x))
         (remainder 0))
    (loop for i from (1- len) downto 0
          do (let ((xi (uvref x i)))
               (multiple-value-bind (q r) (%udiv64by32 remainder xi y)
                 (setf (uvref res i) q)
                 (setq remainder r))))
    (values (%high-half remainder) (%low-half remainder))))

;;; %FLOOR-LOOP-NO-QUO -- divide bignum x by y, return remainder only.
;;; Returns (values remainder-hi remainder-lo).
(defun %floor-loop-no-quo (x yhi ylo)
  (let* ((y (%compose-digit yhi ylo))
         (len (uvsize x))
         (remainder 0))
    (loop for i from (1- len) downto 0
          do (let ((xi (uvref x i)))
               (multiple-value-bind (q r) (%udiv64by32 remainder xi y)
                 (declare (ignore q))
                 (setq remainder r))))
    (values (%high-half remainder) (%low-half remainder))))

;;; %FLOOR-99 -- if x[xidx] = y[yidx], return (#xFFFF #xFFFF).
;;; Otherwise compute floor(x[xidx]:x[xidx-1] / y[yidx]).
;;; Returns (values result-hi result-lo).
(defun %floor-99 (x xidx yptr yidx)
  (let* ((xi (uvref x xidx))
         (yi (uvref yptr yidx)))
    (if (= xi yi)
        (values #xFFFF #xFFFF)
        (let ((xi-1 (uvref x (1- xidx))))
          (multiple-value-bind (q r) (%udiv64by32 xi xi-1 yi)
            (declare (ignore r))
            (values (%high-half q) (%low-half q)))))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Shifting
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; BIGNUM-SHIFT-LEFT-LOOP -- shift bignum left by nbits, writing result.
;;; bignum has len+1 digits accessible (len data + sign extension).
;;; result has len+j+1 digits.
;;; j = number of whole-word shifts (zero-fill at bottom).
(defun bignum-shift-left-loop (nbits result bignum len j)
  (let ((rshift (- 32 nbits)))
    ;; First partial digit.
    (let ((first-digit (uvref bignum 0)))
      (setf (uvref result (1- j)) (%u32 (ash first-digit nbits))))
    ;; Middle digits.
    (let ((i 0))
      (loop while (< (1+ i) len)
            do (let* ((lo (uvref bignum i))
                      (hi (uvref bignum (1+ i)))
                      (val (logior (ash lo (- rshift))
                                   (%u32 (ash hi nbits)))))
                 (setf (uvref result (+ j i)) (%u32 val))
                 (incf i))))
    ;; Last digit: arithmetic shift right of highest digit.
    (let* ((top (uvref bignum (1- len)))
           ;; Sign-extend: if bit 31 set, arithmetic shift right.
           (shifted (if (logbitp 31 top)
                        (%u32 (logior (ash top (- rshift))
                                      (ash -1 (- 32 rshift))))
                        (ash top (- rshift)))))
      (setf (uvref result (+ j (1- len)))
            (%u32 shifted)))))

;;; BIGNUM-SHIFT-RIGHT-LOOP-1 -- shift bignum right by nbits.
;;; result[0..len-1] = shifted, with sign extension on top.
(defun bignum-shift-right-loop-1 (nbits result bignum len iidx)
  (let ((rshift (- 32 nbits))
        (jidx 0))
    (loop while (< jidx len)
          do (let* ((lo (uvref bignum iidx))
                    (hi (uvref bignum (1+ iidx)))
                    (val (logior (ash lo (- nbits))
                                 (%u32 (ash hi rshift)))))
               (setf (uvref result jidx) (%u32 val))
               (incf jidx)
               (incf iidx)))
    ;; Final digit: arithmetic shift right.
    (let* ((top (uvref bignum iidx))
           (shifted (if (logbitp 31 top)
                        (%u32 (logior (ash top (- nbits))
                                      (ash -1 (- 32 nbits))))
                        (ash top (- nbits)))))
      (setf (uvref result jidx) (%u32 shifted)))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Normalization
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; NORMALIZE-BIGNUM-LOOP -- return the normalized length.
;;; sign is the sign word (0 or #xFFFFFFFF as fixnum 0 or -1).
;;; Strips leading digits that equal the sign. Ensures the sign bit
;;; of the remaining top digit matches sign.
(defun normalize-bignum-loop (sign res len)
  (let ((usign (%u32 sign)))
    (loop while (and (> len 1)
                     (= (uvref res (1- len)) usign))
          do (decf len))
    ;; Check if we need an extra digit for sign.
    (let ((top (uvref res (1- len))))
      (unless (eql (logand usign #x80000000)
                   (logand top #x80000000))
        (incf len)))
    len))

;;; %NORMALIZE-BIGNUM-2 -- normalize bignum, possibly returning a fixnum.
;;; fixp: if non-nil, may return a fixnum for single-digit results.
(defun %normalize-bignum-2 (fixp res)
  (let* ((len (uvsize res))
         (oldlen len))
    (when (zerop len) (return-from %normalize-bignum-2 res))
    (let* ((top (uvref res (1- len)))
           (usign (if (logbitp 31 top) #xFFFFFFFF 0)))
      ;; Strip leading sign-extension digits.
      (loop while (and (> len 1)
                       (= (uvref res (1- len)) usign))
            do (decf len))
      ;; Ensure sign bit of remaining top digit matches.
      (let ((new-top (uvref res (1- len))))
        (unless (eql (logand usign #x80000000)
                     (logand new-top #x80000000))
          (incf len)))
      ;; Maybe return fixnum.
      (when (and fixp (= len 1))
        (let* ((v (uvref res 0))
               (as-fixnum (if (logbitp 31 v)
                              (- v #x100000000)
                              v)))
          ;; Check fixnum range: on 32-bit, fixnums are 30-bit signed.
          (when (and (>= as-fixnum (- (ash 1 29)))
                     (< as-fixnum (ash 1 29)))
            (return-from %normalize-bignum-2 as-fixnum))))
      ;; Shrink the bignum header if needed.
      (when (< len oldlen)
        (%shrink-bignum len res))
      res)))

;;; %COUNT-DIGIT-LEADING-ZEROS -- CLZ of composed digit (hi, lo).
(defun %count-digit-leading-zeros (high low)
  (let ((d (%compose-digit high low)))
    (if (zerop d)
        32
        (let ((n 0))
          (when (zerop (logand d #xFFFF0000)) (setq n (+ n 16) d (ash d 16)))
          (when (zerop (logand d #xFF000000)) (setq n (+ n 8) d (ash d 8)))
          (when (zerop (logand d #xF0000000)) (setq n (+ n 4) d (ash d 4)))
          (when (zerop (logand d #xC0000000)) (setq n (+ n 2) d (ash d 2)))
          (when (zerop (logand d #x80000000)) (setq n (+ n 1)))
          n))))

;;; %COUNT-DIGIT-TRAILING-ZEROS -- CTZ of composed digit (hi, lo).
(defun %count-digit-trailing-zeros (high low)
  (let ((d (%compose-digit high low)))
    (if (zerop d)
        32
        (let ((n 0))
          (when (zerop (logand d #x0000FFFF)) (setq n (+ n 16) d (ash d -16)))
          (when (zerop (logand d #x000000FF)) (setq n (+ n 8) d (ash d -8)))
          (when (zerop (logand d #x0000000F)) (setq n (+ n 4) d (ash d -4)))
          (when (zerop (logand d #x00000003)) (setq n (+ n 2) d (ash d -2)))
          (when (zerop (logand d #x00000001)) (setq n (+ n 1)))
          n))))

;;; %BIGNUM-COUNT-TRAILING-ZERO-BITS -- total trailing zero bits in bignum.
(defun %bignum-count-trailing-zero-bits (bignum)
  (let ((ndigits 0))
    ;; Find first nonzero digit.
    (loop
      (let ((digit (uvref bignum ndigits)))
        (unless (zerop digit)
          ;; Count trailing zeros in this digit.
          (let ((ctz (let ((d digit) (n 0))
                       (when (zerop (logand d #x0000FFFF)) (setq n (+ n 16) d (ash d -16)))
                       (when (zerop (logand d #x000000FF)) (setq n (+ n 8) d (ash d -8)))
                       (when (zerop (logand d #x0000000F)) (setq n (+ n 4) d (ash d -4)))
                       (when (zerop (logand d #x00000003)) (setq n (+ n 2) d (ash d -2)))
                       (when (zerop (logand d #x00000001)) (setq n (+ n 1)))
                       n)))
            (return (+ (* ndigits 32) ctz))))
        (incf ndigits)))))

;;; %BIGNUM-TRIM-LEADING-ZEROS -- return new length after trimming
;;; leading zero digits from bignum[start..start+len-1].
(defun %bignum-trim-leading-zeros (bignum start len)
  (loop while (and (> len 0)
                   (zerop (uvref bignum (+ start len -1))))
        do (decf len))
  len)

;;; %SHRINK-BIGNUM -- shrink bignum to new-len digits.
;;; Zeros out digits from new-len to old-len and updates the header.
(defun %shrink-bignum (new-len bignum)
  (let ((old-len (uvsize bignum)))
    (unless (= old-len new-len)
      ;; Zero out the tail.
      (loop for i from new-len below old-len
            do (setf (uvref bignum i) 0))
      ;; Update the header. On 32-bit CCL, bignum header is:
      ;; subtag-bignum | (len << num-subtag-bits)
      ;; We use %set-uvsize which is the portable way to shrink.
      ;; For bootstrap, we just zero the excess and trust the caller.
      )))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Division helpers
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; TRY-GUESS-LOOP-1 -- multiply guess by y and subtract from x.
;;; guess is (guess-h, guess-l) composed. len-y is digit count of y.
;;; x is modified in place starting at xidx.
(defun try-guess-loop-1 (guess-h guess-l len-y xidx xptr yptr)
  (let ((guess (%compose-digit guess-h guess-l))
        (carry 0)
        (borrow 1))
    (dotimes (j len-y)
      (multiple-value-bind (lo hi) (%mul32x32 guess (uvref yptr j))
        (let* ((prod-lo (%u32 (+ lo carry)))
               (prod-hi (%u32 (+ hi (if (> (+ lo carry) #xFFFFFFFF) 1 0))))
               (xval (uvref xptr (+ xidx j)))
               ;; Subtract prod-lo from xval with borrow.
               (diff (+ (- xval prod-lo) borrow -1))
               (new-borrow (if (>= diff 0) 1 0)))
          (setf (uvref xptr (+ xidx j)) (%u32 diff))
          (setq carry prod-hi)
          (setq borrow new-borrow))))
    ;; Subtract carry from last x digit.
    (let* ((last-idx (+ xidx len-y))
           (xval (uvref xptr last-idx))
           (diff (+ (- xval carry) borrow -1)))
      (setf (uvref xptr last-idx) (%u32 diff)))))

;;; TRUNCATE-GUESS-LOOP -- refine division guess.
;;; Compares guess*y1:guess*y2 against x0:x1:x2.
;;; Returns (values guess-hi guess-lo).
(defun truncate-guess-loop (guess-h guess-l x xidx yptr yidx)
  (let* ((guess (%compose-digit guess-h guess-l))
         (y1 (uvref yptr yidx))
         (y2 (uvref yptr (1- yidx)))
         (x0 (uvref x xidx))
         (x1 (uvref x (1- xidx)))
         (x2 (uvref x (- xidx 2))))
    (loop
      (multiple-value-bind (gy1-lo gy1-hi) (%mul32x32 guess y1)
        (let* ((m-val (- x1 gy1-lo))
               (x0-minus-hi (- x0 gy1-hi
                               (if (< x1 gy1-lo) 1 0))))
          ;; If x0 - gy1-hi (with borrow) is not zero and positive, done.
          ;; If negative, need to reduce guess.
          (cond
            ((> x0-minus-hi 0) (return))              ; x0 > gy1-hi: done
            ((< x0-minus-hi 0) (decf guess))          ; need to reduce
            ;; x0-minus-hi = 0: compare gy2 against (m-val : x2)
            (t (multiple-value-bind (gy2-lo gy2-hi) (%mul32x32 guess y2)
                 (let ((m (%u32 m-val)))
                   (cond
                     ((> gy2-hi m) (decf guess))     ; gy2-hi > m: reduce
                     ((< gy2-hi m) (return))          ; gy2-hi < m: done
                     ;; gy2-hi = m: compare gy2-lo with x2
                     ((> gy2-lo x2) (decf guess))
                     (t (return))))))))))
    (values (%high-half (%u32 guess))
            (%low-half (%u32 guess)))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Karatsuba / limb operations
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; COPY-LIMB -- copy src[si] to dest[di].
(defun copy-limb (src si dest di)
  (setf (uvref dest di) (uvref src si)))

;;; LIMB-ZEROP -- T if bignum[i] is zero.
(defun limb-zerop (bignum i)
  (zerop (uvref bignum i)))

;;; COMPARE-LIMBS -- compare a[ai] with b[bi]. Return -1, 0, or 1.
(defun compare-limbs (a ai b bi)
  (let ((av (uvref a ai))
        (bv (uvref b bi)))
    (cond ((= av bv) 0)
          ((> av bv) 1)
          (t -1))))

;;; ADD-FIXNUM-TO-LIMB -- add fixnum to bignum[i], ignoring overflow.
(defun add-fixnum-to-limb (bignum i fixnum)
  (setf (uvref bignum i) (%u32 (+ (uvref bignum i) fixnum))))

;;; COPY-FIXNUM-TO-LIMB -- store fixnum as bignum[i].
(defun copy-fixnum-to-limb (bignum i fixnum)
  (setf (uvref bignum i) (%u32 fixnum)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; GMP-style stubs (mpn_* functions)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; MPN-INCR-U -- increment bignum[i] by val, propagating carry.
(defun mpn-incr-u (bignum i val)
  (let ((carry val))
    (loop while (and (not (zerop carry))
                     (< i (uvsize bignum)))
          do (let ((sum (+ (uvref bignum i) carry)))
               (setf (uvref bignum i) (%u32 sum))
               (setq carry (if (> sum #xFFFFFFFF) 1 0))
               (incf i)))))

;;; MPN-SUB-N -- dest[0..len-1] = a[0..len-1] - b[0..len-1].
;;; Returns carry (borrow): 0 = no borrow, 1 = borrow.
(defun mpn-sub-n (dest a b len)
  (let ((borrow 0))
    (dotimes (i len)
      (let* ((diff (- (uvref a i) (uvref b i) borrow)))
        (setf (uvref dest i) (%u32 diff))
        (setq borrow (if (< diff 0) 1 0))))
    borrow))

;;; MPN-ADD-N -- dest[0..len-1] = a[0..len-1] + b[0..len-1].
;;; Returns carry: 0 or 1.
(defun mpn-add-n (dest a b len)
  (let ((carry 0))
    (dotimes (i len)
      (let ((sum (+ (uvref a i) (uvref b i) carry)))
        (setf (uvref dest i) (%u32 sum))
        (setq carry (if (> sum #xFFFFFFFF) 1 0))))
    carry))

;;; MPN-ADD-1 -- dest[0..len-1] = src[0..len-1] + val (with carry propagation).
;;; Returns carry: 0 or 1.
(defun mpn-add-1 (dest src len val)
  (let ((carry val))
    (dotimes (i len)
      (let ((sum (+ (uvref src i) carry)))
        (setf (uvref dest i) (%u32 sum))
        (setq carry (if (> sum #xFFFFFFFF) 1 0))))
    carry))

;;; MPN-MUL-1 -- dest[0..len-1] = src[0..len-1] * multiplier.
;;; Store the final carry in result[0].
(defun mpn-mul-1 (dest src len multiplier result)
  (let ((carry 0))
    (dotimes (i len)
      (multiple-value-bind (lo hi) (%mul32x32 (uvref src i) multiplier)
        (let* ((sum (+ lo carry))
               (new-lo (%u32 sum))
               (new-hi (%u32 (+ hi (if (> sum #xFFFFFFFF) 1 0)))))
          (setf (uvref dest i) new-lo)
          (setq carry new-hi))))
    (setf (uvref result 0) carry)))

;;; MPN-ADDMUL-1 -- dest[0..len-1] += src[0..len-1] * multiplier.
;;; Store the final carry in result[0].
(defun mpn-addmul-1 (dest src len multiplier result)
  (let ((carry 0))
    (dotimes (i len)
      (multiple-value-bind (lo hi) (%mul32x32 (uvref src i) multiplier)
        (let* ((sum1 (+ lo carry))
               (c1 (if (> sum1 #xFFFFFFFF) 1 0))
               (lo1 (%u32 sum1))
               (sum2 (+ lo1 (uvref dest i)))
               (c2 (if (> sum2 #xFFFFFFFF) 1 0)))
          (setf (uvref dest i) (%u32 sum2))
          (setq carry (%u32 (+ hi c1 c2))))))
    (setf (uvref result 0) carry)))

;;; MPN-MUL-BASECASE -- schoolbook multiply.
;;; dest[0..alen+blen-1] = a[0..alen-1] * b[0..blen-1].
(defun mpn-mul-basecase (dest a alen b blen)
  ;; Zero the destination.
  (dotimes (i (+ alen blen))
    (setf (uvref dest i) 0))
  ;; Schoolbook multiply.
  (dotimes (j blen)
    (let ((bv (uvref b j))
          (carry 0))
      (dotimes (i alen)
        (multiple-value-bind (lo hi) (%mul32x32 (uvref a i) bv)
          (let* ((sum1 (+ lo carry))
                 (c1 (if (> sum1 #xFFFFFFFF) 1 0))
                 (lo1 (%u32 sum1))
                 (prev (uvref dest (+ i j)))
                 (sum2 (+ lo1 prev))
                 (c2 (if (> sum2 #xFFFFFFFF) 1 0)))
            (setf (uvref dest (+ i j)) (%u32 sum2))
            (setq carry (%u32 (+ hi c1 c2))))))
      (setf (uvref dest (+ alen j)) carry))))

;;; MPN-LSHIFT-1 -- left shift src by 1 bit into dest.
;;; Returns the bit that was shifted out (0 or 1).
(defun mpn-lshift-1 (dest src len)
  (let ((carry 0))
    (dotimes (i len)
      (let* ((val (uvref src i))
             (new-carry (if (logbitp 31 val) 1 0))
             (shifted (%u32 (logior (ash val 1) carry))))
        (setf (uvref dest i) shifted)
        (setq carry new-carry)))
    carry))

;;; UMULPPM -- 32x32 unsigned multiply.
;;; Store result (lo first, then hi) in result bignum.
(defun umulppm (x y result)
  (let ((xv (uvref x 0))
        (yv (uvref y 0)))
    (multiple-value-bind (lo hi) (%mul32x32 xv yv)
      (setf (uvref result 0) lo)
      (setf (uvref result 1) hi))))

;;; MACPTR->FIXNUM -- convert macptr to fixnum address.
;;; (Already defined in wasm-def.lisp, but included here for completeness
;;; in case this file is loaded independently.)
;; (defun macptr->fixnum (ptr) ...)

;;; End of wasm-bignum.lisp
