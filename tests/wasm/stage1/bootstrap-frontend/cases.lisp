(in-package :ccl)

;;; Small semantic witnesses supplement the unchanged source definitions.
;;; None of these definitions is counted in bootstrap throughput.
(defparameter *frontend-cases*
  '(("macro_scope"
     (lambda (x)
       (macrolet ((pick (form) `(car ,form)))
         (symbol-macrolet ((value (pick x)))
           (let ((value (cdr x)))
             (values value (pick x)))))))
    ("setf_order"
     (lambda (x)
       (let ((log nil))
         (setf (car (progn (push 1 log) x))
               (progn (push 2 log) 7))
         (values x log))))
    ("setf_value"
     (lambda (x)
       (values (setf (car x) (cdr x)) x)))
    ("setf_cdr"
     (lambda (x)
       (values (setf (cdr x) (car x)) x)))
    ("cond_values"
     (lambda (x)
       (cond ((car x) (values (car x) (cdr x)))
             (t (values)))))
    ("case_nil"
     (lambda (x)
       (case x
         (nil 1)
         (t 2))))
    ("typed_values"
     (lambda (x)
       (the (values t t) (values x (cdr x)))))
    ("not_eq"
     (lambda (x)
       (values (not (eq (car x) (cdr x))) (not x) (not (not x)))))
    ("defaults"
     (lambda (x &optional (y (when x (car x))))
       (declare (ignorable x))
       y))
    ("local_macro"
     (lambda (x)
       (macrolet ((choose (y) `(if ,y 17 23)))
         (flet ((choose (y) (car y)))
           (choose x)))))
    ("target_word"
     (lambda () target::node-size))))
