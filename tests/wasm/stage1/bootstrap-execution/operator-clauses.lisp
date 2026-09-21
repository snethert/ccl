      ((ccl::char-code ccl::%char-code ccl::code-char ccl::%code-char ccl::%valid-code-char)
       (bootstrap-character op args))
      ((ccl::%sbchar ccl::%scharcode ccl::%set-sbchar ccl::%set-scharcode)
       (bootstrap-string-access op args))
      ((ccl::%typed-uvref ccl::%typed-uvset) (bootstrap-array-operator op args))
      ((ccl::%unbound-marker ccl::%symbol->symptr ccl::%symptr->symvector ccl::%symvector->symptr)
       (bootstrap-symbol-operator op args))
      (ccl::neq
       (bootstrap-operands (cdr args)
         (lambda (values)
           (bootstrap-boolean (b-wat "(i32.eq ~a ~a)" (first values) (second values))
                              (ccl::acode-immediate-operand (car args))))))
      ((ccl::int>0-p ccl::%izerop)
       (bootstrap-operands (cdr args)
         (lambda (values)
           (b-wat "~a ~a"
                  (b-condition (b-wat "(i32.and ~a (i32.const 3))" (car values)) 5)
                  (bootstrap-boolean
                   (b-wat "(i32.~a ~a (i32.const 0))"
                          (if (eq op 'ccl::%izerop) "eq" "gt_s") (car values))
                   (if (eq op 'ccl::%izerop)
                     (ccl::acode-immediate-operand (car args)) :eq))))))
      ((ccl::add2 ccl::sub2 ccl::mul2 ccl::div2)
       (bootstrap-primary
        (bootstrap-numeric-call
         (ecase op (ccl::add2 '+) (ccl::sub2 '-) (ccl::mul2 '*) (ccl::div2 '/)) args)))
      (ccl::numcmp
       (bootstrap-primary
        (bootstrap-numeric-call
         (ecase (ccl::acode-immediate-operand (car args))
           (:lt '<) (:le '<=) (:eq '=) (:ne '/=) (:ge '>=) (:gt '>)) (cdr args))))
