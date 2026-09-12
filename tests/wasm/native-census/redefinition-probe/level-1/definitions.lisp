(in-package :cl-user)
(eval-when (:compile-toplevel :load-toplevel :execute)
  (defun dependency-version (x) (+ x 20))
  (defmacro dependency-macro (x) `(+ ,x 20)))
