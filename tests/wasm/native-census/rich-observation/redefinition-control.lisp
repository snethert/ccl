;;; Reproduce the first collector defect without repeating a whole native build.
(in-package :cl-user)
(defun run-rich-redefinition-control (path mutant &optional (name 'ccl::%lfun-info-index))
  (let ((original (symbol-function name))
        (original-unfhave (symbol-function 'ccl::%unfhave)) (caught nil) (returned nil))
    (unwind-protect
        (progn
          (when mutant
            ;; Reintroduce the unsafe observation point after the primitive has
            ;; cleared the cell. Both metadata and ordinary logger helpers are
            ;; legitimate functions for CCL itself to replace during a build.
            (setf (symbol-function 'ccl::%unfhave)
                  (lambda (target)
                    (multiple-value-prog1 (funcall original-unfhave target)
                      (when (eq target name)
                        (ccl-rich-census::observe :binding-installed (list target original)))))))
          (ccl-rich-census::start path)
          (handler-case
              (progn (setf (symbol-function name) original) (setq returned t))
            (error (condition) (setq caught condition))))
      (setf ccl::*startup-census-hook* nil)
      (ccl::%fhave 'ccl::%unfhave original-unfhave)
      (ccl::%fhave name original))
    (if mutant
      (assert (and (not returned) (typep caught 'undefined-function)))
      (assert (and returned (null caught)))))
  (ccl-rich-census::finish)
  (format t "REDEFINITION-CONTROL ~a~%" (if mutant "REJECTED" "PASS")))
