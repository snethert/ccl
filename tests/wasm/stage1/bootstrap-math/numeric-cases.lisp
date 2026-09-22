      ((ccl::%single-float ccl::%double-float)
       (bootstrap-primary
        (b-float-call (if (eq op 'ccl::%single-float) '%float-single '%float-double)
                      (list (car args) (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 0)))))
      ((ccl::natural-shift-left ccl::natural-shift-right)
       (bootstrap-natural-shift op args))
      (ccl::minus1
       (bootstrap-primary (bootstrap-subtract args)))
