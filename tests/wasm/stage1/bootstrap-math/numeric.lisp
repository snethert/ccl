;;; Natural shifts operate on one unsigned target word, not a tagged fixnum.
(defun bootstrap-unbox-word (value)
  (let ((p (temporary)) (h (temporary)) (w (temporary)))
    (b-wat "(block (result i32)
      (if (result i32) (i32.eqz (i32.and ~a (i32.const 3)))
        (then ~a (i32.shr_u ~a (i32.const 2)))
        (else ~a (local.set ~a (i32.sub ~a (i32.const 6)))
          (call $span (local.get ~a) (i32.const 8))
          (local.set ~a (i32.load (local.get ~a)))
          (local.set ~a (i32.load offset=4 (local.get ~a)))
          (if (i32.eq (local.get ~a) (i32.const 263))
            (then ~a)
            (else ~a (call $span (local.get ~a) (i32.const 16)) ~a))
          (local.get ~a))))"
      value (b-condition (b-wat "(i32.lt_s ~a (i32.const 0))" value) 32) value
      (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" value) 32)
      p value p h p w p h
      (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) (i32.const 536870912)) (i32.gt_u (local.get ~a) (i32.const 2147483647)))" w w) 32)
      (b-condition (b-wat "(i32.ne (local.get ~a) (i32.const 519))" h) 32) p
      (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) (i32.const 2147483648)) (i32.load offset=8 (local.get ~a)))" w p) 32) w)))

(defun bootstrap-natural-shift (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (value count) values
        (let ((word (temporary)))
          (b-wat "~a (local.set ~a ~a) ~a"
                 (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" count count) 5)
                 word (bootstrap-unbox-word value)
                 (bootstrap-box-word
                  (b-wat "(if (result i32) (i32.ge_u ~a (i32.const 128)) (then (i32.const 0)) (else (i32.~a (local.get ~a) (i32.shr_u ~a (i32.const 2)))))"
                         count (if (eq op 'ccl::natural-shift-left) "shl" "shr_u") word count) nil)))))))

(defun bootstrap-word-logical (name forms)
  (when (and (= (length forms) 2)
             (every (lambda (form) (ccl::acode-form-typep form '(unsigned-byte 32) t)) forms))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (bootstrap-box-word
            (b-wat "(i32.~a ~a ~a)" (ecase name (logand "and") (logior "or") (logxor "xor"))
                   (bootstrap-unbox-word (first values)) (bootstrap-unbox-word (second values))) nil)))))))

;;; The result argument of the native destructive float primitives is rooted
;;; across calculation. Copy only after both operands have been evaluated.
(defun bootstrap-float-store (forms)
  (unless (= (length forms) 2) (refuse :bootstrap-float-store-arity))
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (result value) values
        (let ((kind (temporary)) (dst (temporary)) (src (temporary)))
          (b-wat "(local.set ~a (call $real_operand ~a)) ~a ~a
                   (local.set ~a (i32.sub ~a (i32.const 6)))
                   (local.set ~a (i32.sub ~a (i32.const 6)))
                   (if (i32.eq (local.get ~a) (i32.const 32))
                     (then (i32.store offset=4 (local.get ~a) (i32.load offset=4 (local.get ~a))))
                     (else (i64.store offset=8 (local.get ~a) (i64.load offset=8 (local.get ~a))))) ~a"
                 kind result
                 (b-condition (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 32)) (i32.ne (local.get ~a) (i32.const 64)))" kind kind) 4)
                 (b-condition (b-wat "(i32.ne (call $real_operand ~a) (local.get ~a))" value kind) 4)
                 dst result src value kind dst src dst src result))))))
