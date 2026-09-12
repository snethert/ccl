(in-package :cl-user)
(eval-when (:compile-toplevel :load-toplevel :execute)
  (setf (fdefinition 'dependency-version) (lambda (x) (+ x 30)))
  (defmacro dependency-macro (x) `(+ ,x 30)))
