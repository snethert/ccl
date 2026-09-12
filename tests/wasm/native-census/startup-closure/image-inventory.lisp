;;; Read-only inspection of a clean native image in a disposable process.
;;; Load ../observer.lisp for its JSON writer, but never call START or save an image.
(defpackage :ccl-image-inventory (:use :cl)
  (:import-from :ccl-startup-census #:object #:json #:label-of))
(in-package :ccl-image-inventory)

(defun full-label (value)
  (if (or (symbolp value) (pathnamep value) (stringp value))
    (label-of value)
    (let ((*print-circle* t) (*print-pretty* nil) (*print-readably* nil)
          (*print-level* nil) (*print-length* nil) (*package* (find-package :keyword)))
      (write-to-string value))))

(defun inspect-image (output)
  (when ccl::*startup-census-hook* (error "Observation hook must be disabled"))
  (ccl:gc)
  (let ((functions nil) (ids (make-hash-table :test #'eq))
        (bindings nil) (seen-symbols (make-hash-table :test #'eq))
        (backend ccl::*target-backend*))
    ;; Keep every heap code prototype, including anonymous functions, methods,
    ;; closures' code and inspector functions. No address-taken pruning.
    (ccl::%map-lfuns (lambda (fn)
                      (unless (gethash fn ids)
                        (setf (gethash fn ids) (1+ (hash-table-count ids)))
                        (push fn functions))))
    (setf functions (nreverse functions))
    (labels ((function-id (fn)
               (unless (functionp fn) (error "Not a function: ~s" fn))
               (let ((code (ccl::closure-function fn)))
                 (or (gethash code ids)
                     (error "Function code missing from heap inventory: ~s" fn))))
             (binding (sym &optional setter)
               (let ((fn (fboundp sym)) (macro (macro-function sym)))
                 (when (functionp fn)
                   (push (object "name" (label-of sym)
                                 "setter_of" (if setter (label-of setter) :null)
                                 "namespace" "function" "function" (function-id fn)) bindings))
                 (when macro
                   (push (object "name" (label-of sym) "setter_of" :null
                                 "namespace" "macro" "function" (function-id macro)) bindings)))))
      (do-all-symbols (sym)
        (unless (gethash sym seen-symbols)
          (setf (gethash sym seen-symbols) t)
          (binding sym)))
      ;; Use the existing map: SETF-FUNCTION-NAME would create missing bindings.
      ;; Preserve both the package-qualified original and uninterned cell name.
      (maphash (lambda (original cell) (binding cell original)) ccl::%setf-function-names%)
      (with-open-file (stream output :direction :output :if-exists :error
                              :external-format :utf-8)
        (json
         (object
          "version" 1 "backend" (label-of (ccl::backend-name backend))
          "scope" "All resident native code prototypes after loading the inspector; includes inspector code. A snapshot, not a bound on arbitrary future EVAL, FASL loading, or rebinding."
          "functions"
          (loop for fn in functions collect
            (let ((note (ccl:function-source-note fn)) (literals nil))
              (ccl::%map-lfimms fn
                (lambda (imm)
                  (when (functionp imm) (pushnew (function-id imm) literals))))
              (object "id" (gethash fn ids) "name" (full-label (ccl:function-name fn))
                      "source" (if note (full-label (ccl::source-note-filename note)) :null)
                      "source_position" (if note (ccl::source-note-start-pos note) :null)
                      "literal_functions" (sort literals #'<))))
          "bindings" (reverse bindings)
          "startup_groups"
          (loop for (group fns) in
                (list (list "system_pointers" (reverse ccl::*lisp-system-pointer-functions*))
                      (list "restore_lisp" ccl::*restore-lisp-functions*)
                      (list "user_pointers" (reverse ccl::*lisp-user-pointer-functions*))
                      (list "startup" (reverse ccl:*lisp-startup-functions*))) collect
            (object "group" group "functions"
                    (loop for fn in fns collect
                      (object "name" (label-of fn)
                              "function" (function-id (if (symbolp fn) (symbol-function fn) fn))))))
          "operators"
          (let ((dispatch (ccl::backend-p2-dispatch backend)))
            (loop for entry in (reverse ccl::*next-nx-operators*) for id from 0
                  for handler = (and (< id (length dispatch)) (svref dispatch id)) collect
              (object "id" id "name" (if entry (label-of (car entry)) :null)
                      "flags" (if entry (cadr entry) 0)
                      "encoded" (if entry (gethash (car entry) ccl::*nx1-operators*) :null)
                      "handler" (label-of handler)
                      "function" (if handler
                                   (function-id (if (symbolp handler) (symbol-function handler) handler)) :null))))
          "vinsns"
          (loop for name being the hash-keys of (ccl::backend-p2-vinsn-templates backend)
                using (hash-value cell) for template = (cdr cell) collect
            (object "name" (label-of name)
                    "defined" (if template :true :false)
                    "attributes" (if template (ccl::vinsn-template-attributes template) :null)
                    "body" (if template (full-label (ccl::vinsn-template-body template)) :null)
                    "opcodes" (if template (full-label (ccl::vinsn-template-opcode-alist template)) :null)))
          "vinsn_attribute_names" (mapcar #'label-of ccl::*known-vinsn-attributes*)
          "subprimitives"
          (loop for info across (arch::target-subprims-table (ccl::backend-target-arch backend)) collect
            (object "name" (ccl::subprimitive-info-name info)
                    "offset" (ccl::subprimitive-info-offset info)))) stream)
        (terpri stream))
      (format t "IMAGE-INVENTORY functions=~d bindings=~d~%" (length functions) (length bindings)))))
