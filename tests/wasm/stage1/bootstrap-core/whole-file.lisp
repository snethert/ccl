(in-package :wasm32-compiler)

(defvar *core-modules* nil)
(defvar *core-files* nil)
(defvar *core-records* nil)
(defvar *core-native-functions* (make-hash-table :test #'eq))

;;; Use CCL's file compiler to establish its own compile-time environments.
;;; The diagnostic sink retains module records rather than writing a native
;;; fasl. No target definition is installed in the host Lisp.
(defun core-compile-file (path &optional native)
  (let ((ccl:*warn-if-redefine-kernel* nil)
        (file-compiler (fdefinition 'ccl::fcomp-file))
        (function-compiler (fdefinition 'ccl::fcomp-named-function))
        (done (gensym "FILE")))
    (unwind-protect
        (progn
          (setf (fdefinition 'ccl::fcomp-named-function)
                (lambda (definition name env &optional source-note)
                  (block core-native-entry
                  (when native
                    (let ((function (funcall function-compiler definition name env source-note)))
                      (when name (setf (gethash name *core-native-functions*) function))
                      (return-from core-native-entry function)))
                  (let* ((wire (format nil "core_~d" (length *core-records*)))
                         (result nil)
                         (outcome (handler-case
                                      (progn
                                        (setq result (compile-bootstrap-form definition wire nil env))
                                        :admitted)
                                    (unsupported-wasm32-code (c)
                                      (unsupported-operation c))
                                    (error (c) (list (type-of c) (format nil "~a" c))))))
                    (push (list path name wire outcome (and result (getf result :dependencies))) *core-records*)
                    (when result
                      (setf (getf result :source-name) name
                            (getf result :source-file) path)
                      (push result *core-modules*))
                    ;; FCOMP's output records are never dumped as native fasl.
                    ;; This is a sink token, not executable placeholder code.
                    (list :wasm-module wire outcome)))))
          (setf (fdefinition 'ccl::fcomp-file)
                (lambda (&rest args)
                  (let ((records (apply file-compiler args)))
                    (push (list path records) *core-files*)
                    (throw done records))))
          (flet ((compile-source ()
                   (catch done
                     (apply #'compile-file path :verbose nil :print nil
                            :output-file (merge-pathnames "unused.wfsl" path)
                            (unless native '(:target :wasm32))))))
            (if native (compile-source) (call-with-target #'compile-source))))
      (setf (fdefinition 'ccl::fcomp-file) file-compiler
            (fdefinition 'ccl::fcomp-named-function) function-compiler))))
