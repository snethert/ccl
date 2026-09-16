;;; Witness the bootstrap image's deferred marker before nfcomp replaces it.
(defpackage :ccl-initial-marker (:use :cl))
(in-package :ccl-initial-marker)

(defun run ()
  (let* ((directory (ccl:getenv "CCL_MARKER_OUTPUT"))
         (input (translate-logical-pathname "ccl:lib;compile-ccl.lisp"))
         (mode (ccl:getenv "CCL_MARKER_MODE"))
         (output (concatenate 'string directory "/" mode ".dx64fsl"))
         (writer (fdefinition 'ccl::fasl-out-opcode))
         (reader (fdefinition 'ccl::%fasl-dispatch))
         (ccl::*warn-if-redefine* nil) (ccl::*warn-if-redefine-kernel* nil))
    (if (equal mode "reference")
      (ccl-deferred-probes::compile-input input output nil)
      (ccl-complete-census::with-build-observation
        (concatenate 'string directory "/build.jsonl")
        (concatenate 'string directory "/registries.jsonl")
        (lambda ()
          (let* ((token ccl::cfasl-load-time-eval-sym) (macro (fboundp token)))
            (unless (and (simple-vector-p macro) (= (length macro) 2) (functionp (svref macro 1)))
              (error "INITIAL-MARKER-WRAPPER"))
            (ccl-complete-census::function-id (svref macro 1))
            (ccl-complete-census::function-id (fdefinition 'ccl::xload-level-0))
            (ccl-complete-census::emit "deferred-marker-read"
              "symbol" (ccl-startup-census::dependency-id token)
              "symbol_description" (ccl-rich-census::describe-value token)
              "macro" (ccl-rich-census::describe-value macro)))
          (unwind-protect
            (progn
              (setf (fdefinition 'ccl::fasl-out-opcode)
                (lambda (opcode form)
                  (when (functionp form)
                    (ccl-complete-census::observe :fasl-function-write
                      (list (namestring ccl::*fasdump-stream*) (ccl::fasl-filepos) opcode form)))
                  (funcall writer opcode form)))
              (setf (fdefinition 'ccl::%fasl-dispatch)
                (lambda (state op) (ccl-method-reload::observe-read reader state op)))
              (ccl-deferred-probes::compile-input input output t)
              (load output :verbose nil :print nil))
            (setf (fdefinition 'ccl::fasl-out-opcode) writer
                  (fdefinition 'ccl::%fasl-dispatch) reader)))))
    (format t "INITIAL-MARKER-PASS~%")))
