;;; A separately compiled load unit, including a captured function and effect.
(defvar *p2-0-second-effect* nil)
(defun p2-0-second (x)
  (let ((f (lambda (y) (cons x (cons y nil)))))
    (funcall f 42)))
(setq *p2-0-second-effect* (p2-0-second 9))
