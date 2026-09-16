(in-package :ccl-deferred-probes)

(defun read-left (instance) (slot-value instance 'left))
(defun class-object () (find-class 'box))
(defun shared-list () (load-time-value (list :retained :data)))
(defun callable-result () (load-time-value #'1+))
(defun nested-value () (load-time-value (list (load-time-value (list :nested)))))
