(in-package :cl-user)
(eval-when (:compile-toplevel :load-toplevel :execute)
  (defun dependency-bootstrap (x) (+ x 10))
  (ccl::%fhave 'dependency-version #'dependency-bootstrap)
  (defmacro dependency-macro (x) `(+ ,x 10)))
;; A quoted DEFUN is data and must not be reported as a definition.
(defparameter *dependency-definition-data* '(defun dependency-quoted () :data))
