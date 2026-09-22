(in-package :wasm32-compiler)

(defun bootstrap-float-sign (name forms)
  (unless (= (length forms) 1) (refuse :float-sign-arity))
  (let ((doublep (eq name 'ccl::%double-float-sign)))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((object (first values)))
             (b-wat "~a ~a"
               (b-condition (b-wat "(i32.ne (call $real_operand ~a) (i32.const ~d))"
                                  object (if doublep 64 32)) 4)
               (bootstrap-boolean
                (b-wat "(i32.shr_u (i32.load offset=~d (i32.sub ~a (i32.const 6))) (i32.const 31))"
                       (if doublep 12 4) object))))))))))
