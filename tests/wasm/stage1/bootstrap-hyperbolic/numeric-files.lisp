(in-package :wasm32-compiler)

;;; Use the real file environments for the numeric implementation. An entry
;;; refused here must not fall back to its old standalone compilation.
(dolist (path '("ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp" "ccl:level-1;l1-numbers.lisp"))
  (core-compile-file path t))
(let ((previous *core-records*) (names nil))
  (dolist (path '("ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp"
                  "ccl:level-0;l0-bignum32.lisp" "ccl:level-1;l1-numbers.lisp"))
    (core-compile-file path))
  (loop for tail on *core-records* until (eq tail previous) do
    (let ((name (second (car tail))))
      (when (and name (symbolp name))
        (pushnew name names)
        ;; The 64-bit image supplies the mathematical bignum counterpart.
        ;; Other entries use the same file's native compile, not a later
        ;; definition that happens to occupy its symbol in the saved image.
        (when (and (equal (first (car tail)) "ccl:level-0;l0-bignum32.lisp")
                   (fboundp name))
          (setf (gethash name *core-native-functions*) (fdefinition name))))))
  (setq *core-candidates*
        (remove-if (lambda (row) (member (second (first row)) names))
                   *core-candidates*)))
