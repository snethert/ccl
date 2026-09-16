;;; Exact COMPILE-INPUT body from the reviewed source-closure driver.
(defpackage :ccl-cold-bodies (:use :cl))
(in-package :ccl-cold-bodies)

(defun compile-input (path)
  ;; Bind the front-end state from U1 %COMPILE-FILE, stopping before FASL scan.
  (let* ((ccl::*fasl-deferred-warnings* nil) (ccl::*fasl-save-local-symbols* nil)
         (ccl::*save-source-locations* t) (ccl::*fasl-save-doc-strings* nil)
         (ccl::*fasl-save-definitions* nil) (ccl::*fasl-break-on-program-errors* t)
         (ccl::*fcomp-warnings-header* nil) (*compile-file-pathname* path)
         (*compile-file-truename* (truename path)) (*package* *package*) (*readtable* (copy-readtable))
         (*compile-print* nil) (*compile-verbose* nil)
         (ccl::*fasl-backend* ccl::*target-backend*)
         (ccl::*fasl-target-big-endian* nil)
         (ccl::*fasl-compile-time-env* (ccl::new-lexical-environment (ccl::new-definition-environment)))
         (ccl::*fcomp-external-format* :utf-8) (ccl::*fasl-setf-name-alias-alist* nil)
         (ccl::*outstanding-deferred-warnings* (ccl::%defer-warnings nil))
         (defenv (ccl::new-definition-environment)) (env (ccl::new-lexical-environment defenv)))
    (rplacd (ccl::defenv.type defenv) ccl::*outstanding-deferred-warnings*)
    (setf (ccl::defenv.defined defenv) (ccl::deferred-warnings.defs ccl::*outstanding-deferred-warnings*))
    (ccl::fcomp-file (namestring path) (namestring path) nil env)))

(defun outputs (rows destination)
  (with-open-file (s destination :direction :output :if-exists :error)
    (ccl-rich-census::write-json
      (ccl-startup-census::object "opcodes" (mapcar #'car rows)
        "functions"
        (loop for row in rows for index from 0 when (member (car row) '(4 35 37)) collect
          (let ((fn (second row)))
            (unless (functionp fn) (error "COLD-BODY-OUTPUT-FUNCTION"))
            (ccl-startup-census::object "index" index "opcode" (car row)
              "code" (subseq (ccl-resident-bodies::payload-hex fn
                               (ccl::uvsize (ccl::%function-to-function-vector fn)))
                             0 (* 16 (ccl::%function-code-words fn))))))) s)
    (terpri s)))

(defun compile-one (input destination observed)
  (let* ((backend ccl::*host-backend*) (old (ccl::backend-p2-compile backend))
         (ccl::*target-backend* backend) (ccl::*fasl-target* (ccl::backend-name backend))
         (*features* (ccl::setup-target-features backend *features*))
         (*gensym-counter* 100000)
         (saved-dump (fdefinition 'ccl::fasl-scan-forms-and-dump-file))
         (ccl::*warn-if-redefine-kernel* nil))
    (unwind-protect
      (progn
        (setf (fdefinition 'ccl::fasl-scan-forms-and-dump-file)
              (lambda (&rest args) (declare (ignore args)) (error "COLD-BODY-FASL-FORBIDDEN")))
        (when observed
          (setf (ccl::backend-p2-compile backend)
            (lambda (afunc &rest args)
              (let ((*gensym-counter* *gensym-counter*))
                (ccl-complete-census::observe :before-pass2 afunc))
              (multiple-value-prog1 (apply old afunc args)
                (let ((*gensym-counter* *gensym-counter*))
                  (ccl-complete-census::observe :function-materialized afunc))))))
        (ccl::with-cross-compilation-target ((ccl::backend-name backend))
          (outputs (compile-input input) destination)))
      (setf (ccl::backend-p2-compile backend) old
            (fdefinition 'ccl::fasl-scan-forms-and-dump-file) saved-dump))
    (unless (and (eq old (ccl::backend-p2-compile backend))
                 (eq saved-dump (fdefinition 'ccl::fasl-scan-forms-and-dump-file)))
      (error "COLD-BODY-OBSERVER-RESTORATION"))))

(defun run ()
  (let* ((input (pathname (ccl:getenv "CCL_COLD_INPUT")))
         (directory (ccl:getenv "CCL_COLD_OUTPUT"))
         (observed (equal (ccl:getenv "CCL_COLD_MODE") "observed")))
    (if observed
      (ccl-complete-census::with-build-observation
        (concatenate 'string directory "/build.jsonl")
        (concatenate 'string directory "/registries.jsonl")
        (lambda () (compile-one input (concatenate 'string directory "/outputs.json") t)))
      (compile-one input (concatenate 'string directory "/outputs.json") nil))
    (format t "COLD-BODY-PASS ~a~%" input)))
