;;; Whole-file arithmetic calls. Expected arithmetic uses the existing generic
;;; integer operations; the calls under test name the loaded CCL definitions.
(defun loader-bignum-arithmetic (bits sign-a sign-b)
  (let* ((a (* sign-a (+ (ash 1 bits) #xffff)))
         (b (* sign-b (+ (ash 1 (- bits 17)) #x10001))))
    (values (= (add-bignums a b) (+ a b))
            (= (subtract-bignum a b) (- a b))
            (= (multiply-bignums a b) (* a b))
            (= (multiply-bignums a a) (* a a))
            (= (add-bignum-and-fixnum a -19) (+ a -19))
            (= (multiply-bignum-and-fixnum a -7) (* a -7))
            (bignum-compare a b))))

(defun loader-bignum-logical (sign)
  (let* ((a (* sign (+ (ash 1 96) #xffff)))
         (b (+ (ash 1 72) #x10001)))
    (values (= (bignum-logical-and a b) (logand a b))
            (= (bignum-logical-ior a b) (logior a b))
            (= (bignum-logical-xor a b) (logxor a b))
            (= (bignum-logical-not a) (lognot a))
            (= (negate-bignum a) (- a))
            (bignum-logtest a b)
            (bignum-logcount a)
            (bignum-integer-length a))))

(defun loader-bignum-shifts (count sign)
  (let ((a (* sign (+ (ash 1 96) #x10001))))
    (values (= (bignum-ashift-left a count) (ash a count))
            (= (bignum-ashift-right a count) (ash a (- count)))
            (= (copy-bignum a) a)
            (eq (copy-bignum a) a)
            (one-bignum-factor-of-two (ash a 35)))))

(defun loader-bignum-divide (sign-a sign-b)
  (let* ((a (* sign-a (+ (ash 1 130) (ash 1 72) 12345)))
         (b (* sign-b (+ (ash 1 70) 17)))
         (expected-q (* (* sign-a sign-b)
                        #.(truncate (+ (ash 1 130) (ash 1 72) 12345)
                                    (+ (ash 1 70) 17))))
         (expected-r (* sign-a
                        #.(rem (+ (ash 1 130) (ash 1 72) 12345)
                               (+ (ash 1 70) 17)))))
    (multiple-value-bind (q r) (bignum-truncate a b)
      (values (= q expected-q) (= r expected-r)
              (= (bignum-rem a b) expected-r)
              (= (bignum-truncate-no-rem a b) expected-q)))))

(defun loader-bignum-gcd ()
  (let* ((factor (+ (ash 1 80) 1))
         (a (* factor 15)) (b (* factor 21)))
    (values (= (%bignum-bignum-gcd a b) (* factor 3))
            (= (%bignum-bignum-gcd (- a) b) (* factor 3))
            (bignum-fixnum-gcd a 45))))

(defun loader-bignum-pressure (count)
  (let ((a (+ (ash 1 96) 65535)) (b (+ (ash 1 80) 17)) (sum 0))
    (dotimes (i count)
      (setq sum (add-bignums a b))
      (setq a (subtract-bignum sum b)))
    (values (= a (+ (ash 1 96) 65535)) (= sum (+ a b)))))

(defun loader-markers ()
  (let ((a (%unbound-marker)) (b (%slot-unbound-marker)) (c (%illegal-marker)))
    (values (eq a b) (eq a c) (eq b c) (eq c (%illegal-marker)))))

(defun loader-cfm-byte-length ()
  (values (byte-length "") (byte-length "loader")
          (external-entry-point-p nil)))

;;; QLFUN publishes an xfunction before the enclosing initializer's pass 2.
;;; Preserve that exact function as a constant in the initializer's pool.
(defun loader-literal-original (x) (+ x 37))
(defvar *loader-literal-function* nil)
(setq *loader-literal-function*
      (qlfun loader-literal-constant (x) (+ x 37)))
(defun loader-literal-other (x) (- x 11))
(defun loader-literal-call (x)
  (values (funcall *loader-literal-function* x)
          (eq *loader-literal-function* #'loader-literal-original)))

;;; Target-only refusals: a checked error must propagate through Lisp cleanup.
#+wasm32-target
(defvar *loader-pointer-cleanups* 0)

#+wasm32-target
(defun loader-pointer-allow (&rest args)
  (declare (ignore args))
  19)

#+wasm32-target
(defun loader-pointer-boundary (operation)
  (unwind-protect
       (case operation
         (0 (mpn-sqr-basecase 0 0 2))
         (1 (mpn-kara-sqr-n 0 0 2 0))
         (2 (mpn-kara-mul-n 0 0 0 2 0))
         (3 (mpn-sqr-n 0 0 2))
         (4 (mpn-mul-n 0 0 0 2))
         (5 (mpn-mul 0 0 2 0 2))
         (6 (unsignedwide->integer nil))
         (7 (entry->addr 0 nil))
         (8 (foreign-symbol-entry "loader-symbol"))
         (9 (foreign-symbol-address "loader-symbol"))
         (10 (refresh-external-entrypoints))
         (11 (open-shared-library-internal "loader-library")))
    (incf *loader-pointer-cleanups*)))
