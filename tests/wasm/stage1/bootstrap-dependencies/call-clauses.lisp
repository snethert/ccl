          ((member name '(ccl::%symptr-value ccl::%set-symptr-value))
           (unless (= (length forms) (if (eq name 'ccl::%symptr-value) 1 2))
             (refuse :bootstrap-symbol-arity))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-operands forms
                (lambda (values)
                  (let ((location (b-wat "(call $special_location ~a)" (first values))))
                    (if (eq name 'ccl::%symptr-value)
                      (b-wat "(i32.load ~a)" location)
                      (b-wat "(i32.store ~a ~a) ~a" location (second values) (second values)))))))))
          ((member name '(type-error-datum type-error-expected-type
                         simple-condition-format-control simple-condition-format-arguments))
           (bootstrap-condition-reader name forms))
          ((and (member name '(1+ 1-)) (= (length forms) 1))
           (bootstrap-numeric-call (if (eq name '1+) '+ '-)
             (append forms (list (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 1)))))
          ((and (member name '(zerop ccl::%short-float-zerop ccl::%double-float-zerop))
                (= (length forms) 1))
           (bootstrap-numeric-call '=
             (append forms (list (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 0)))))
