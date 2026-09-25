;;; Compilation-owned function constants may cross initializer boundaries,
;;; but neither native functions nor another compilation's xfunctions enter.
(in-package "WASM32-COMPILER")
(defvar ccl::*loader-test-literal* nil)
(let* ((out (ccl:getenv "LOADER_OUTPUT"))
       ;; FASLs retain the source name even without source-location notes.
       ;; Use the same stable logical pathname convention as the other files.
       (source "ccl:tests;wasm;stage1;loader-level0;literal-control.lisp")
       (fasl (concatenate 'string out "literal-control.w32fsl"))
       (publish (symbol-function 'wasm32-xfunction))
       (outer (list :outer-compilation))
       (*wasm32-fasl-functions* outer)
       (rows nil))
  (with-open-file (s source :direction :output :if-exists :supersede)
    (write-line "(defun ccl::loader-control-original (x) (+ x 1))" s))
  (unwind-protect
       (progn
         (setf (symbol-function 'wasm32-xfunction)
               (lambda (module)
                 (setq ccl::*loader-test-literal* (funcall publish module))))
         (multiple-value-bind (path modules warnings failure)
             (wasm32-compile-file source :output-file fasl)
           (declare (ignore modules warnings))
           (assert (and path (not failure)))))
    (setf (symbol-function 'wasm32-xfunction) publish))
  (assert (eq outer *wasm32-fasl-functions*))
  (with-open-file (s source :direction :output :if-exists :supersede)
    (write-line "(defun ccl::loader-invalid-literal () #.ccl::*loader-test-literal*)" s))
  (dolist (kind '("foreign-compilation" "native-function"))
    (when (equal kind "native-function")
      (setq ccl::*loader-test-literal* #'car))
    (let ((reason
            (handler-case
                (progn (wasm32-compile-file source :output-file fasl) nil)
              (unsupported-wasm32-code (condition) (unsupported-operation condition)))))
      (assert (eq reason :heap-constant))
      (assert (eq outer *wasm32-fasl-functions*))
      (push (list :object (cons "name" kind) (cons "reason" (string reason))
                  (cons "scope_restored" t)) rows)))
  (with-open-file (s (concatenate 'string out "literal-controls.json")
                     :direction :output :if-exists :supersede)
    (ccl::wasm32-json (reverse rows) s) (terpri s)))
