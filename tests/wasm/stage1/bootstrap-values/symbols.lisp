(in-package :wasm32-compiler)

(defun bootstrap-symbol (symbol)
  ;; Imports name owner-supplied identities, not package lookups at run time.
  ;; The module record retains the actual symbol, including uninterned ones.
  (unless (symbolp symbol) (refuse :bootstrap-symbol))
  (let ((entry (assoc symbol *bootstrap-symbols*)))
    (unless entry
      (setq entry (list symbol (format nil "bootstrap_~d" (length *bootstrap-symbols*))))
      (push entry *bootstrap-symbols*))
    (pushnew (second entry) *b-symbols* :test #'equal)
    (b-wat "(global.get $symbol_~a)" (second entry))))
