(in-package :wasm32-compiler)

;;; The existing typed accessors define these D1 layouts. Generic UVREF and
;;; allocation must use the same representation when CCL selects a stream's
;;; element type at run time.
(defparameter *namespace-integer-vectors*
  '((199 1 :unsigned-8-bit-vector 0 255)
    (207 1 :signed-8-bit-vector -128 127)
    (215 2 :unsigned-16-bit-vector 0 65535)
    (223 2 :signed-16-bit-vector -32768 32767)
    (167 4 :unsigned-32-bit-vector 0 4294967295)
    (175 4 :signed-32-bit-vector -2147483648 2147483647)
    (183 4 :fixnum-vector -536870912 536870911)))

(defun bootstrap-integer-vector-value (value subtag low high)
  (cond ((= subtag 167) (bootstrap-unbox-word value))
        ((= subtag 175)
         (let ((base (temporary)))
           (b-wat "(if (result i32) (i32.eqz (i32.and ~a (i32.const 3)))
              (then (i32.shr_s ~a (i32.const 2)))
              (else (local.set ~a (call $object_base ~a (i32.const 8) (i32.const 263)))
                    (i32.load offset=4 (local.get ~a))))" value value base value base)))
        (t
         (b-wat "~a ~a"
           (b-condition
            (b-wat "(i32.or (i32.and ~a (i32.const 3))
                      (i32.or (i32.lt_s ~a (i32.const ~d))
                              (i32.gt_s ~a (i32.const ~d))))"
                   value value (* 4 low) value (* 4 high)) 5)
           (if (= subtag 183) value (b-wat "(i32.shr_s ~a (i32.const 2))" value))))))

(defun bootstrap-integer-vector (values layout)
  (destructuring-bind (count tag &optional initial) values
    (declare (ignore tag))
    (destructuring-bind (subtag width kind low high) layout
      (declare (ignore kind))
      (let ((word (temporary)) (n (temporary)) (i (temporary)))
        (b-wat "~a (local.set ~a (i32.shr_u ~a (i32.const 2)))
          (local.set ~a ~a) (i32.add ~a (i32.const 6))"
          (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3))
                                (i32.gt_u ~a (i32.const 67108860)))" count count) 6)
          n count word (if initial (bootstrap-integer-vector-value initial subtag low high) "(i32.const 0)")
          (bootstrap-heap-block
           (b-wat "(i32.and (i32.add (i32.mul (local.get ~a) (i32.const ~d))
                                    (i32.const 11)) (i32.const -8))" n width)
           (lambda (base bytes)
             (b-wat "(memory.fill ~a (i32.const 0) ~a)
               (i32.store ~a (i32.or (i32.shl (local.get ~a) (i32.const 8)) (i32.const ~d)))
               (local.set ~a (i32.const 0))
               (block $integer_vector_done (loop $integer_vector_fill
                 (br_if $integer_vector_done (i32.ge_u (local.get ~a) (local.get ~a)))
                 (i32.store~a (i32.add ~a (i32.add (i32.const 4)
                   (i32.mul (local.get ~a) (i32.const ~d)))) (local.get ~a))
                 (local.set ~a (i32.add (local.get ~a) (i32.const 1)))
                 (br $integer_vector_fill)))"
               base bytes base n subtag i i n (case width (1 "8") (2 "16") (t ""))
               base i width word i i))))))))

(defun bootstrap-make-vector (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((raw (mapcar (lambda (x) (make-b-raw-code :text x)) values)))
        (reduce (lambda (layout fallback)
                  (b-wat "(if (result i32) (i32.eq ~a (i32.const ~d)) (then ~a) (else ~a))"
                         (second values) (* 4 (first layout))
                         (bootstrap-integer-vector values layout) fallback))
                *namespace-integer-vectors* :from-end t
                :initial-value (bootstrap-make-simple-vector raw))))))

(defun bootstrap-uvector-access (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((tag (temporary))
            (raw (mapcar (lambda (x) (make-b-raw-code :text x)) values)))
        (b-wat "(local.set ~a ~a) ~a" tag (bootstrap-typecode (first values))
          (reduce (lambda (layout fallback)
                    (b-wat "(if (result i32) (i32.eq (local.get ~a) (i32.const ~d))
                              (then ~a) (else ~a))"
                           tag (* 4 (first layout))
                           (bootstrap-typed-access
                            (if (third values) 'ccl::%typed-uvset 'ccl::%typed-uvref)
                            (cons (bootstrap-constant (third layout)) raw))
                           fallback))
                  *namespace-integer-vectors* :from-end t
                  :initial-value (bootstrap-basic-uvector-access op raw)))))))
