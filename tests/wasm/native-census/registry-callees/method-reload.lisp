;;; Compile and reload one native source unit; all wrappers forward unchanged.
(defpackage :ccl-method-reload (:use :cl))
(in-package :ccl-method-reload)

(defun reader-context (state op)
  (list (ccl::faslstate.faslfname state) op (ccl::%fasl-get-file-pos state)
    (cond ((eq (ccl::faslstate.fasldispatch state) ccl::*fasl-dispatch-table*) :native)
          (t :other))
    (svref (ccl::faslstate.fasldispatch state) op)))

(defun observe-read (original state op)
  (let ((base (logand op (lognot (ash 1 ccl::$fasl-epush-bit)))))
    (if (/= base ccl::$fasl-clfun)
      (funcall original state op)
      (let ((completed nil))
        (ccl-complete-census::observe :fasl-function-enter (reader-context state base))
        (unwind-protect
          (multiple-value-prog1 (funcall original state op) (setq completed t))
          (let* ((context (reader-context state base))
                 (result (append (subseq context 0 3)
                           (list (ccl::faslstate.faslval state)) (nthcdr 3 context))))
            (ccl-complete-census::observe
              (if completed :fasl-function-return :fasl-function-abort) result)))))))

(defun source-rows (requested)
  (let ((result nil) (ccl::*direct-methods-only* t))
    (ccl::%map-lfuns
      (lambda (fn)
        (let ((ident (ccl-startup-census::dependency-id fn)))
          (when (member ident requested)
            (unless (logbitp 28 (ccl::lfun-bits fn)) (error "RELOAD-NOT-METHOD"))
            (let* ((method (ccl::%method-function-method fn))
                   (sources (ccl:find-definition-sources method 'method)))
              (push (ccl-startup-census::object "function" ident
                "method" (ccl-startup-census::dependency-id method)
                "sources" (loop for entry in sources append
                  (progn
                    (unless (eq (cdar entry) method) (error "RELOAD-SOURCE-IDENTITY"))
                    (loop for src in (cdr entry) collect
                      (cond ((ccl:source-note-p src)
                             (ccl-startup-census::object "file" (namestring (ccl:source-note-filename src))
                               "start" (ccl:source-note-start-pos src) "end" (ccl:source-note-end-pos src)))
                            ((or (stringp src) (pathnamep src))
                             (ccl-startup-census::object "file" (namestring (pathname src))
                               "start" :null "end" :null))
                            (t (error "RELOAD-SOURCE-KIND"))))))) result))))))
    (unless (= (length result) (length requested)) (error "RELOAD-MISSING-METHOD"))
    (nreverse result)))

(defun run ()
  (let* ((input (ccl:getenv "CCL_RELOAD_INPUT"))
         (directory (ccl:getenv "CCL_RELOAD_OUTPUT"))
         (requested (read-from-string (ccl:getenv "CCL_RELOAD_METHODS")))
         (reference (concatenate 'string directory "/reference.dx64fsl"))
         (observed (concatenate 'string directory "/observed.dx64fsl"))
         (writer (fdefinition 'ccl::fasl-out-opcode))
         (reader (fdefinition 'ccl::%fasl-dispatch))
         (ccl::*warn-if-redefine-kernel* nil)
         (ccl::*warn-if-redefine* nil))
    (when (equal (ccl:getenv "CCL_RELOAD_MODE") "reference")
      (ccl-deferred-probes::compile-input input reference nil)
      (format t "METHOD-REFERENCE-PASS~%")
      (return-from run))
    (ccl-complete-census::with-build-observation
      (concatenate 'string directory "/build.jsonl")
      (concatenate 'string directory "/registries.jsonl")
      (lambda ()
        (with-open-file (stream (concatenate 'string directory "/method-sources.json")
                          :direction :output :if-exists :error)
          (ccl-rich-census::write-json (source-rows requested) stream) (terpri stream))
        (unwind-protect
          (progn
            (setf (fdefinition 'ccl::fasl-out-opcode)
              (lambda (opcode form)
                (when (functionp form)
                  (ccl-complete-census::observe :fasl-function-write
                    (list (namestring ccl::*fasdump-stream*) (ccl::fasl-filepos) opcode form)))
                (funcall writer opcode form)))
            (setf (fdefinition 'ccl::%fasl-dispatch)
              (lambda (state op) (observe-read reader state op)))
            (ccl-deferred-probes::compile-input input observed t)
            (load observed :verbose nil :print nil))
          (setf (fdefinition 'ccl::fasl-out-opcode) writer
                (fdefinition 'ccl::%fasl-dispatch) reader))
        (unless (and (eq (fdefinition 'ccl::fasl-out-opcode) writer)
                     (eq (fdefinition 'ccl::%fasl-dispatch) reader))
          (error "RELOAD-IO-HOOKS-NOT-RESTORED"))))
    (format t "METHOD-RELOAD-PASS~%")))
