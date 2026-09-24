          ((eq name 'ccl::%wasm-thread-local-value)
           (unless (= (length forms) 1) (refuse :thread-local-value-arity))
           (b-multiple (make-b-raw-code :text
            (bootstrap-operands
            forms
            (lambda (values)
              (let ((location (temporary)) (symbol (first values)))
                (b-wat "(block (result i32)
                          (local.set ~a (call $special_location ~a))
                          (if (result i32) (i32.eq (local.get ~a)
                                                  (i32.add ~a (i32.const 2)))
                            (then (i32.const 77825))
                            (else (i32.load (local.get ~a)))))"
                       location symbol location symbol location)))))))
