;;; Synthetic control inputs. These are never represented as U1 source.
(in-package :ccl-census-query)
(defun probe-forward (fn x) (funcall fn x))
(defun probe-spread (fn args) (apply fn args))
(defun probe-order (provider left right) (funcall (funcall provider) (funcall left) (funcall right)))
(defun probe-symbol (name effect) (funcall name (funcall effect)))
(defun probe-closure (fn) (lambda (x) (funcall fn x)))
(defun probe-unwind (fn cleanup) (unwind-protect (funcall fn) (funcall cleanup)))
