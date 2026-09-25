;;; Observation only: the wrapper delegates unchanged to CCL's function compiler.
(in-package :ccl)
(in-development-mode
  (load "ccl:lib;systems.lisp")
  (load "ccl:lib;compile-ccl.lisp")
  (dolist (name '("wasm32-arch" "wasm32-backend" "nfcomp" "xfasload" "xwasm32fasload"))
    (load (concatenate 'string "ccl:bin;" name ".dx64fsl"))))

(let* ((*warn-if-redefine-kernel* nil)
       (compiler (fdefinition 'fcomp-named-function))
       (current-name "")
       (context nil)
       (result nil)
       (output (getenv "CROSS_LOAD_RESULT")))
  (unwind-protect
      (progn
        (setf (fdefinition 'fcomp-named-function)
              (lambda (definition name environment &optional note)
                (setq current-name (format nil "~s" name))
                (funcall compiler definition name environment note)))
        (setq result
              (handler-case
                  (handler-bind
                      ((error (lambda (condition)
                                (unless context (setq context
                                      (list (if (typep condition 'reader-error) "READ" "COMPILE")
                                            current-name *fcomp-stream-position*
                                            (format nil "~a" condition)))))))
                    (with-cross-compilation-target (:wasm32)
                      (let ((*target-backend* (find-backend :wasm32))
                            (*nx-speed* (max 1 *nx-speed*))
                            (*nx-safety* (min 1 *nx-safety*))
                            (*save-doc-strings* t) (*fasl-save-doc-strings* t))
                        (in-development-mode
                          (multiple-value-bind (path warnings failure)
                              (compile-file (getenv "CROSS_LOAD_FILE") :target :wasm32
                                            :features *xcompile-features* :verbose t :print t
                                            :output-file (concatenate 'string output ".w32fsl"))
                            (declare (ignore warnings))
                            (if (and path (not failure))
                              (list "PASS" "COMPILE" "" 0 "")
                              (cons "REFUSED" (or context (list "COMPILE" current-name 0 "COMPILE-FILE failure")))))))))
                (error (condition)
                  (cons "REFUSED" (or context (list "COMPILE" current-name 0 (format nil "~a" condition))))))))
    (setf (fdefinition 'fcomp-named-function) compiler))
  (with-open-file (stream (concatenate 'string output ".json")
                          :direction :output :if-exists :error)
    (wasm32-xload-json result stream)))
(quit)
