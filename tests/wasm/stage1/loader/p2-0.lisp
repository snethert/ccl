;;; NSL-2 P2-0: one ordinary DEFUN with constants and one top-level effect.
;;; No IN-PACKAGE: SET-PACKAGE is a level-0 call and would be the first stop
;;; (the producer and the oracle read this file in the CCL package).

(defvar *p2-0-effect* nil)

(defun p2-0-answer (x)
  (cons x (cons "constant" (cons 'p2-0-answer '(42)))))

(setq *p2-0-effect* (p2-0-answer 7))
