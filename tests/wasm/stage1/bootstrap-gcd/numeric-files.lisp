(in-package :wasm32-compiler)

;;; Use the real file environments for the numeric implementation. An entry
;;; refused here must not fall back to its old standalone compilation.
(dolist (path '("ccl:level-1;l1-error-system.lisp" "ccl:level-1;l1-error-signal.lisp" "ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp" "ccl:level-1;l1-numbers.lisp" "ccl:level-1;l1-aprims.lisp" "ccl:level-1;l1-clos-boot.lisp" "ccl:level-1;l1-dcode.lisp"))
  (if (equal path "ccl:level-1;l1-aprims.lisp")
    (let ((saved (loop for name being the hash-keys of *core-native-functions*
                      using (hash-value function) collect (cons name function))))
      (core-compile-file path t)
      ;; Keep each existing oracle paired with the source definition its
      ;; target module uses. L1-APRIMS redefines some earlier numeric names.
      (dolist (entry saved)
        (unless (eq (car entry) 'ccl::lfun-keyvect)
          (setf (gethash (car entry) *core-native-functions*) (cdr entry)))))
    (core-compile-file path t)))
(let ((previous *core-records*) (names nil))
  (dolist (path '("ccl:level-1;l1-error-system.lisp" "ccl:level-1;l1-error-signal.lisp" "ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp"
                  "ccl:level-0;l0-bignum32.lisp" "ccl:level-1;l1-numbers.lisp" "ccl:level-1;l1-aprims.lisp" "ccl:level-1;l1-clos-boot.lisp" "ccl:level-1;l1-dcode.lisp"))
    (if (equal path "ccl:level-1;l1-error-signal.lisp")
      (handler-case (core-compile-file path)
        (error (condition)
          ;; Preserve the existing foreign-reader boundary. Only definitions
          ;; emitted before it are candidates; this file is not complete.
          (format t "KERNEL-RESTART-FILE-STOP ~a~%" condition)))
      (core-compile-file path)))
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
