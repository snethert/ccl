(in-package :wasm32-compiler)

;;; Raw digit access is the target equivalent of the native bignum LAP entries.
;;; No allocation or callback follows validation and precedes a digit store.
(defun bootstrap-bignum-base (object)
  (let ((base (temporary)) (count (temporary)))
    (b-wat "(block (result i32) ~a
      (local.set ~a (i32.sub ~a (i32.const 6)))
      (call $span (local.get ~a) (i32.const 4))
      (local.set ~a (i32.shr_u (i32.load (local.get ~a)) (i32.const 8))) ~a ~a
      (call $span (local.get ~a) (i32.and (i32.add (i32.shl (local.get ~a) (i32.const 2)) (i32.const 11)) (i32.const -8)))
      (local.get ~a))"
      (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4)
      base object base count base
      (b-condition (b-wat "(i32.ne (i32.load8_u (local.get ~a)) (i32.const 7))" base) 4)
      (b-condition (b-wat "(i32.eqz (local.get ~a))" count) 4)
      base count base)))

(defun bootstrap-bignum-index (base index)
  (b-condition
   (b-wat "(i32.or (i32.and ~a (i32.const 3))
             (i32.ge_u (i32.shr_u ~a (i32.const 2))
                       (i32.shr_u (i32.load ~a) (i32.const 8))))" index index base) 4))

(defun bootstrap-bignum-call (name forms)
  (let ((arity (case name (ccl::%wasm-bignum-half-ref 3) (ccl::%wasm-bignum-set 4)
                         (ccl::%wasm-bignum-length-set 2) (t 5))))
    (unless (= (length forms) arity) (refuse :bignum-primitive-arity)))
  (bootstrap-operands forms
    (lambda (values)
      (let ((base (temporary)))
        (with-output-to-string (s)
          (format s "(local.set ~a ~a)" base (bootstrap-bignum-base (first values)))
          (case name
            ((ccl::%wasm-bignum-half-ref ccl::%wasm-bignum-set)
             (destructuring-bind (object index high &optional low) values
               (write-string (bootstrap-bignum-index (b-local base) index) s)
               (if low
                 (progn
                   (dolist (part (list high low))
                     (write-string (b-condition (b-wat "(i32.and ~a (i32.const 3))" part) 5) s))
                   (format s "(i32.store (i32.add (local.get ~a) (i32.add (i32.const 4) ~a))
                     (i32.or (i32.shl ~a (i32.const 14)) (i32.and (i32.shr_u ~a (i32.const 2)) (i32.const 65535)))) ~a"
                     base index high low object))
                 (format s "(i32.shl (i32.load16_u (i32.add (local.get ~a)
                   (i32.add ~a (if (result i32) (i32.eq ~a (i32.const 77825)) (then (i32.const 4)) (else (i32.const 6)))))) (i32.const 2))"
                   base index high))))
            (ccl::%wasm-bignum-length-set
             (let ((count (second values)) (old (temporary)) (end (temporary)) (cursor (temporary)))
               (format s "(local.set ~a (i32.shr_u (i32.load (local.get ~a)) (i32.const 8)))" old base)
               (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.eqz ~a) (i32.gt_u (i32.shr_u ~a (i32.const 2)) (local.get ~a))))" count count count old) 4) s)
               ;; Shrinking a header leaves whole aligned objects, never a gap
               ;; that the collector could mistake for an unrecognized header.
               (format s "(local.set ~a (i32.add (local.get ~a) (i32.and (i32.add (i32.shl (local.get ~a) (i32.const 2)) (i32.const 11)) (i32.const -8))))
                 (local.set ~a (i32.add (local.get ~a) (i32.and (i32.add ~a (i32.const 11)) (i32.const -8))))
                 (block $padding_done (loop $padding
                   (br_if $padding_done (i32.ge_u (local.get ~a) (local.get ~a)))
                   (i32.store (local.get ~a) (i32.const 250))
                   (i32.store offset=4 (local.get ~a) (i32.const 0))
                   (local.set ~a (i32.add (local.get ~a) (i32.const 8))) (br $padding)))
                 (if (i32.eqz (i32.and ~a (i32.const 4)))
                   (then (i32.store (i32.add (local.get ~a) (i32.add ~a (i32.const 4))) (i32.const 0))))
                 (i32.store (local.get ~a) (i32.or (i32.shl ~a (i32.const 6)) (i32.const 7))) ~a"
                 end base old cursor base count cursor end cursor cursor cursor cursor count base count base count (first values))))
            (ccl::%copy-ivector-to-ivector
             (destructuring-bind (source start destination to count) values
               (declare (ignore source))
               (let ((dest (temporary)))
                 (format s "(local.set ~a ~a)" dest (bootstrap-bignum-base destination))
                 (dolist (x (list start to count))
                   (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" x x) 4) s))
                 (loop for object in (list (b-local base) (b-local dest))
                       for offset in (list start to) do
                   (write-string (b-condition
                     (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_u ~a))
                        (i64.shl (i64.extend_i32_u (i32.shr_u (i32.load ~a) (i32.const 8))) (i64.const 4)))" offset count object) 4) s))
                 (format s "(memory.copy (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))
                   (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))
                   (i32.shr_u ~a (i32.const 2))) ~a" dest to base start count destination))))))))))

(defun bootstrap-allocate-bignum (forms)
  (when (and (= (length forms) 2) (eql (ccl::acode-fixnum-form-p (second forms)) 7))
    (bootstrap-operands (list (first forms))
      (lambda (values)
        (let ((count (first values)))
          (b-wat "~a (i32.add ~a (i32.const 6))"
            (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.eqz ~a) (i32.gt_u ~a (i32.const 67108860))))" count count count) 6)
            (bootstrap-heap-block
              (b-wat "(i32.and (i32.add ~a (i32.const 11)) (i32.const -8))" count)
              (lambda (base bytes)
                (b-wat "(memory.fill ~a (i32.const 0) ~a) (i32.store ~a (i32.or (i32.shl ~a (i32.const 6)) (i32.const 7)))"
                  base bytes base count)))))))))
