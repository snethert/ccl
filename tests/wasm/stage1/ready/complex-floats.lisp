;;; Native 32-bit complex float objects contain unboxed components. Keep the
;;; input objects rooted until allocation has finished, then reload them.
(defun bootstrap-complex-part (op forms)
  (unless (= (length forms) 1) (refuse :complex-part-arity))
  (let* ((single (member op '(ccl::%complex-single-float-realpart
                              ccl::%complex-single-float-imagpart)))
         (imaginary (member op '(ccl::%complex-single-float-imagpart
                                 ccl::%complex-double-float-imagpart)))
         (size (if single 16 24))
         (header (if single 839 1359))
         (offset (if imaginary (if single 12 16) 8)))
    (bootstrap-operands forms
      (lambda (values)
        (let ((object (car values)))
          (b-wat "(drop (call $object_base ~a (i32.const ~d) (i32.const ~d)))
                   (i32.add ~a (i32.const 6))"
                 object size header
                 (bootstrap-heap-block (if single "(i32.const 8)" "(i32.const 16)")
                   (lambda (base bytes)
                     (b-wat "(memory.fill ~a (i32.const 0) ~a)
                              (i32.store ~a (i32.const ~d))
                              (~a.store offset=~d ~a
                                (~a.load offset=~d (i32.sub ~a (i32.const 6))))"
                            base bytes base (if single 271 791)
                            (if single "i32" "i64") (if single 4 8) base
                            (if single "i32" "i64") offset object)))))))))

(defun bootstrap-complex-float (op forms)
  (unless (= (length forms) 2) (refuse :complex-float-arity))
  (let* ((single (eq op 'ccl::%make-complex-single-float))
         (part-size (if single 8 16))
         (part-header (if single 271 791))
         (size (if single 16 24))
         (header (if single 839 1359))
         (word (if single "i32" "i64")))
    (bootstrap-operands forms
      (lambda (values)
        (destructuring-bind (real imaginary) values
          (b-wat "(drop (call $object_base ~a (i32.const ~d) (i32.const ~d)))
                   (drop (call $object_base ~a (i32.const ~d) (i32.const ~d)))
                   (i32.add ~a (i32.const 6))"
                 real part-size part-header imaginary part-size part-header
                 (bootstrap-heap-block (b-wat "(i32.const ~d)" size)
                   (lambda (base bytes)
                     (b-wat "(memory.fill ~a (i32.const 0) ~a)
                              (i32.store ~a (i32.const ~d))
                              (~a.store offset=8 ~a (~a.load offset=~d (i32.sub ~a (i32.const 6))))
                              (~a.store offset=~d ~a (~a.load offset=~d (i32.sub ~a (i32.const 6))))"
                            base bytes base header
                            word base word (if single 4 8) real
                            word (if single 12 16) base word (if single 4 8) imaginary)))))))))
