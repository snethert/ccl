;;; Dcode is an ordinary callable object in D1. The trampoline uses the
;;; current function's traced immediate vector, just as the native LAP entry.
(defun funcallable-trampoline (&rest args)
  (apply (gf.dcode (%wasm-current-function)) args))

;;; NX1 puts the method context first in the method's lambda-list IR. D1
;;; carries that word in the ordinary rooted argument frame instead of a
;;; native register or an untraced TCR spill slot.
(defun %apply-with-method-context (context function args)
  (apply function context args))

(defun %apply-lexpr-with-method-context (context function args)
  (%apply-lexpr function context args))

(defun %apply-lexpr-tail-wise (function args)
  (%apply-lexpr function args))
