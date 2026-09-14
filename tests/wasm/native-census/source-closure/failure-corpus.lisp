(in-package :cl-user)
(eval-when (:compile-toplevel) (error "CENSUS-DELIBERATE-EFFECT-FAILURE"))
(defun census-after-failure (x) (+ x 1))
