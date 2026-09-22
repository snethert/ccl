;;; Half-digit arithmetic keeps every temporary inside the target fixnum range.
(defun %bignum-ref (bignum index)
  (values (%wasm-bignum-half-ref bignum index t)
          (%wasm-bignum-half-ref bignum index nil)))

(defun %bignum-ref-hi (bignum index)
  (%wasm-bignum-half-ref bignum index t))

(defun %bignum-set (bignum index high low)
  (%wasm-bignum-set bignum index high low))

(defun %bignum-sign (bignum)
  (if (logbitp 15 (%bignum-ref-hi bignum (1- (uvsize bignum)))) -1 0))

(defun bignum-minusp (bignum)
  (< (%bignum-sign bignum) 0))

(defun bignum-plusp (bignum)
  (not (< (%bignum-sign bignum) 0)))

(defun %bignum-oddp (bignum)
  (logbitp 0 (%wasm-bignum-half-ref bignum 0 nil)))

(defun %digit-0-or-plusp (bignum index)
  (not (logbitp 15 (%bignum-ref-hi bignum index))))

(defun %digits-sign-bits (high low)
  (when (logbitp 15 high)
    (setq high (logxor high #xffff) low (logxor low #xffff)))
  (if (zerop high)
    (- 32 (integer-length low))
    (- 16 (integer-length high))))

(defun %bignum-sign-bits (bignum)
  (multiple-value-bind (high low) (%bignum-ref bignum (1- (uvsize bignum)))
    (%digits-sign-bits high low)))

(defun %wasm-bignum-operand (object index)
  (if index
    (%bignum-ref object index)
    (values (logand (ash object -16) #xffff) (logand object #xffff))))

(defun %add-with-carry (result k carry a i b j)
  (multiple-value-bind (ah al) (%wasm-bignum-operand a i)
    (multiple-value-bind (bh bl) (%wasm-bignum-operand b j)
      (let* ((low (+ al bl carry))
             (high (+ ah bh (ash low -16))))
        (%bignum-set result k (logand high #xffff) (logand low #xffff))
        (ash high -16)))))

;;; As on x8632, one means no borrow; zero means an incoming borrow.
(defun %subtract-with-borrow (result k borrow a i b j)
  (multiple-value-bind (ah al) (%wasm-bignum-operand a i)
    (multiple-value-bind (bh bl) (%wasm-bignum-operand b j)
      (multiple-value-bind (high low next) (%subtract-with-borrow-1 ah al bh bl borrow)
        (%bignum-set result k high low)
        next))))

(defun %subtract-with-borrow-1 (ah al bh bl borrow)
  (let* ((low (+ (- al bl) borrow -1))
         (high (+ (- ah bh) (ash low -16))))
    (values (logand high #xffff) (logand low #xffff) (if (< high 0) 0 1))))

(defun %subtract-one (high low)
  (let* ((low (1- low)) (high (+ high (ash low -16))))
    (values (logand high #xffff) (logand low #xffff))))

(defun %add-the-carry (high low carry)
  (let* ((low (+ low carry))
         (high (logand (+ high (ash low -16)) #xffff)))
    ;; The native entry returns its high half sign-extended.
    (values (if (logbitp 15 high) (- high #x10000) high) (logand low #xffff))))

(defun %compare-digits (a b index)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (cond ((> ah bh) 1) ((< ah bh) -1)
            ((> al bl) 1) ((< al bl) -1) (t 0)))))

(defun %normalize-bignum-2 (return-fixnum-p bignum)
  (let ((length (uvsize bignum)))
    (loop while (> length 1) do
      (multiple-value-bind (high low) (%bignum-ref bignum (1- length))
        (let ((sign (if (logbitp 15 (%bignum-ref-hi bignum (- length 2))) #xffff 0)))
          (unless (and (= high sign) (= low sign)) (return))
          (decf length))))
    (%wasm-bignum-length-set bignum length)
    (if (and return-fixnum-p (= length 1))
      (multiple-value-bind (high low) (%bignum-ref bignum 0)
        (if (or (< high #x2000) (>= high #xe000))
          (%ilogior2 (%ilsl 16 high) low)
          bignum))
      bignum)))

(defun %bignum-lognot (index source destination)
  (multiple-value-bind (high low) (%bignum-ref source index)
    (%bignum-set destination index (logxor high #xffff) (logxor low #xffff))))

(defun %bignum-count-trailing-zero-bits (bignum)
  (let ((zeros 0))
    (dotimes (i (uvsize bignum) zeros)
      (multiple-value-bind (high low) (%bignum-ref bignum i)
        (dolist (half (list low high))
          (if (zerop half)
            (incf zeros 16)
            (progn
              (loop until (logbitp 0 half) do (incf zeros) (setq half (ash half -1)))
              (return-from %bignum-count-trailing-zero-bits zeros))))))))

(defun %bignum-logand (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logand ah bh)
                                      (logand al bl)))))

(defun %bignum-logior (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logior ah bh)
                                      (logior al bl)))))

(defun %bignum-logxor (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logxor ah bh)
                                      (logxor al bl)))))

(defun %bignum-logandc1 (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logand (logxor ah #xffff) bh)
                                      (logand (logxor al #xffff) bl)))))

(defun %bignum-logandc2 (index a b destination)
  (multiple-value-bind (ah al) (%bignum-ref a index)
    (multiple-value-bind (bh bl) (%bignum-ref b index)
      (%bignum-set destination index (logand ah (logxor bh #xffff))
                                      (logand al (logxor bl #xffff))))))

(defun %fixnum-to-bignum-set (bignum fixnum)
  (%bignum-set bignum 0 (ash fixnum -16) fixnum)
  fixnum)

(defun bignum-negate-loop-really (bignum length result)
  (let ((carry 1))
    (dotimes (i length carry)
      (multiple-value-bind (high low) (%bignum-ref bignum i)
        (let* ((low (+ (logxor low #xffff) carry))
               (high (+ (logxor high #xffff) (ash low -16))))
          (%bignum-set result i high low)
          (setq carry (ash high -16)))))))

(defun %wasm-half-logcount (half)
  (let ((count 0))
    (loop until (zerop half) do
      (incf count)
      (setq half (logand half (1- half))))
    count))

(defun %logcount (bignum index)
  (multiple-value-bind (high low) (%bignum-ref bignum index)
    (+ (%wasm-half-logcount high) (%wasm-half-logcount low))))

(defun %logcount-complement (bignum index)
  (- 32 (%logcount bignum index)))

(defun %wasm-bignum-half-at (bignum index)
  (cond ((< index 0) 0)
        ((>= index (* 2 (uvsize bignum)))
         (if (bignum-minusp bignum) #xffff 0))
        (t (%wasm-bignum-half-ref bignum (ash index -1) (oddp index)))))

(defun %wasm-bignum-shift-half (bignum index bits leftp)
  (declare (fixnum index bits))
  (multiple-value-bind (words shift) (truncate bits 16)
    (let* ((index (if leftp (- index words) (+ index words)))
           (half (%wasm-bignum-half-at bignum index)))
      (if (zerop shift)
        half
        (logand #xffff
                (if leftp
                  (%ilogior2 (%ilsl shift half)
                             (%ilsr (- 16 shift) (%wasm-bignum-half-at bignum (1- index))))
                  (%ilogior2 (%ilsr shift half)
                             (%ilsl (- 16 shift) (%wasm-bignum-half-at bignum (1+ index))))))))))

(defun bignum-shift-left-loop (nbits result bignum res-len-1 j)
  (let ((digits (1- j)))
    (do ((i digits (1+ i))) ((> i res-len-1) res-len-1)
      (let ((half (* 2 (- i digits))))
        (%bignum-set result i
                     (%wasm-bignum-shift-half bignum (1+ half) nbits t)
                     (%wasm-bignum-shift-half bignum half nbits t))))))

(defun bignum-shift-right-loop-1 (nbits result bignum res-len-1 start)
  (dotimes (i (1+ res-len-1) (+ start res-len-1))
    (let ((half (* 2 (+ start i))))
      (%bignum-set result i
                   (%wasm-bignum-shift-half bignum (1+ half) nbits nil)
                   (%wasm-bignum-shift-half bignum half nbits nil)))))
