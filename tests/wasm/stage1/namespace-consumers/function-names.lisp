;;; Function names are Lisp data. The name in the immutable code pool is the
;;; initial name; per-function changes belong to the target heap.
#+wasm32-target
(defvar *wasm-function-vector-names* nil)

#+wasm32-target
(defun lfun-vector-name (fun &optional (new-name nil set-name-p))
  (if (typep fun 'standard-generic-function)
    (if set-name-p (%gf-name fun new-name) (%gf-name fun))
    (let ((old (if *wasm-function-vector-names*
                 (gethash fun *wasm-function-vector-names* (%wasm-function-name fun))
                 (%wasm-function-name fun))))
      (when set-name-p
        (unless *wasm-function-vector-names*
          (setq *wasm-function-vector-names* (%wasm-make-class-table 16)))
        (puthash fun *wasm-function-vector-names* new-name))
      old)))

#-wasm32-target
