(in-package :census-finite-probes)
(setf *probes*
  (append *probes*
    '(("fdefinition-symbol" finite ("COMMON-LISP::1+")
       (lambda (x) (let ((callee (fdefinition '1+))) (funcall callee x))) ((5)) (6))
      ("symbol-function-symbol" finite ("COMMON-LISP::1-")
       (lambda (x) (let ((callee (symbol-function '1-))) (funcall callee x))) ((5)) (4))
      ("fdefinition-two-names" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
       (lambda (flag x) (let* ((name (if flag '1+ '1-)) (callee (fdefinition name))) (funcall callee x)))
       ((t 5) (nil 5)) (6 4))
      ("fdefinition-dynamic-name" unresolved nil
       (lambda (name x) (let ((callee (fdefinition name))) (funcall callee x))) ((1- 5)) (4))
      ("fdefinition-local-shadow" unresolved nil
       (lambda (x) (flet ((fdefinition (name) (declare (ignore name)) #'1-))
                    (let ((callee (fdefinition '1+))) (funcall callee x)))) ((5)) (4))
      ("lookup-captures-value" finite ("CENSUS-FINITE-PROBES::LOOKUP-PROBE-TARGET")
       (lambda (x) (let ((callee (symbol-function 'lookup-probe-target)))
                     (setf (symbol-function 'lookup-probe-target) #'1-)
                     (funcall callee x))) ((5)) (6)))))
(setf (symbol-function 'lookup-probe-target) #'1+)
