;;; Select the existing checked fixnum tests for statically fixnum operands.
;;; The normal front end supplies the declarations and comparison sense.
(defun bootstrap-fixnum-test (ir)
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir)))
        (args (ccl::acode-operands ir)))
    (case op
      (ccl::numcmp
       (when (every (lambda (x) (ccl::acode-form-typep x 'fixnum t)) (cdr args))
         (ccl::make-acode (ccl::%nx1-operator ccl::%i<>) (first args) (second args) (third args))))
      (ccl::eq
       (let* ((left (second args)) (right (third args))
              (form (cond ((eql (ccl::acode-fixnum-form-p left) 0) right)
                          ((eql (ccl::acode-fixnum-form-p right) 0) left))))
         (when (and form (ccl::acode-form-typep form 'fixnum t))
           (ccl::make-acode (ccl::%nx1-operator ccl::%izerop) (first args) form)))))))
