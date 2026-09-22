      (ccl::global-setq
       (let ((value (temporary)) (symbol (b-special-symbol (first args))))
         (b-wat "(block (result i32) (local.set ~a ~a)
                  (drop (call $object_base ~a (i32.const 32) (i32.const 1850)))
                  (i32.store offset=2 ~a (local.get ~a)) (local.get ~a))"
                value (b-scalar (second args)) symbol symbol value value)))
      (ccl::list*
       (reduce (lambda (head tail) (b-cons head (make-b-raw-code :text tail)))
               (first (first args)) :from-end t
               :initial-value (b-scalar (car (second (first args))))))
      (ccl::vector
       (bootstrap-gvector (cons (bootstrap-constant wasm32::subtag-simple-vector) (car args))))
      (ccl::%make-uvector (bootstrap-make-vector args))
      (ccl::make-list (bootstrap-make-list args))
      (ccl::nth-value
       (let ((*b-tail-position* nil) (*b-producer-target* nil))
         (b-wat "(block (result i32) ~a)"
           (b-frame 1 (lambda (root)
             (let ((index (b-wat "(i32.load offset=8 ~a)" root)))
               (b-wat "(i32.store offset=8 ~a ~a) ~a ~a
                        (if (result i32) (i32.lt_u (i32.shr_u ~a (i32.const 2)) (local.get $count))
                          (then (i32.load (i32.add (local.get $results) ~a))) (else (i32.const 77825)))"
                      root (b-scalar (first args))
                      (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" index index) 5)
                      (b-multiple (second args)) index index)))))))
      (ccl::logbitp
       (bootstrap-operands args
         (lambda (values)
           (destructuring-bind (index value) values
             (b-wat "~a ~a ~a"
                    (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" index index) 5)
                    (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 5)
                    (bootstrap-boolean
                     (b-wat "(if (result i32) (i32.ge_u ~a (i32.const 116)) (then (i32.lt_s ~a (i32.const 0))) (else (i32.and (i32.shr_s ~a (i32.add (i32.shr_u ~a (i32.const 2)) (i32.const 2))) (i32.const 1))))" index value value index)))))))
      ((ccl::%ilsl ccl::%ilsr ccl::%iasr)
       (bootstrap-shift op args))
      ((ccl::uvref ccl::uvset)
       (bootstrap-uvector-access op args))
      ((ccl::%aref1 ccl::aset1 ccl::realpart ccl::imagpart ccl::complex)
       (bootstrap-primary
        (b-call (bootstrap-constant (if (eq op 'ccl::aset1) 'ccl::%aset1 op))
                (list args nil))))
      (ccl::%slot-unbound-marker (b-wat "(i32.const ~d)" wasm32::slot-unbound-marker))
