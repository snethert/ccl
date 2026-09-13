;;; Census-only metadata. No target code, host pointers or kernel offsets.
(defpackage :ccl-census-descriptions (:use :cl))
(defpackage :wasm-census-services (:use :cl))
(in-package :wasm-census)

;; D1/U1: (logior fulltag-nodeheader (ash subtag-index ntagbits)).
(defconstant subtag-basic-stream 50)
(defconstant subtag-instance 114)
(defconstant subtag-struct 122)
(defconstant subtag-istruct 130)
(defconstant min-cl-ivector-subtag 159)
(defconstant subtag-arrayH 234)
(defconstant subtag-vectorH 242)
(defconstant subtag-simple-vector 250)

(in-package :wasm-census-services)
(defun startup-batch-flag ()
  ;; A named dependency, never a fabricated runtime implementation.
  (error "CENSUS-SERVICE-NOT-IMPLEMENTED: STARTUP-BATCH-FLAG"))

(in-package :ccl-census-descriptions)
(defvar *expansions* nil)
(defvar *initializers* nil)
(defvar *initializer-guards* nil)
(defvar *initializer-links* nil)
(defvar *mode* "normal")

(defun capture-deferred-links (afunc)
  (let ((seen (make-hash-table :test #'eq)) (stack (list (ccl::afunc-acode afunc))))
    (loop while stack for node = (pop stack) do
      (cond ((ccl::acode-p node)
             (unless (gethash node seen)
               (setf (gethash node seen) t)
               (let* ((op (ccl::acode-operator-name (ccl::acode-operator node)))
                      (args (ccl::acode-operands node)) (value (car args)))
                 (if (member op '(ccl::immediate ccl::fixnum ccl::nil ccl::t))
                   (when (and (consp value) (eq (car value) ccl::cfasl-load-time-eval-sym))
                     (unless (and (= (length value) 2) (consp (second value))
                                  (= (length (second value)) 2) (eq (car (second value)) 'funcall))
                       (error "CENSUS-UNKNOWN-DEFERRED-LITERAL"))
                     (let* ((record (cdr (assoc (second (second value)) *initializer-guards* :test #'eq)))
                            (owner (ccl-startup-census::dependency-id afunc)))
                       (unless (and record (= owner (ccl-source-traversal::field record "owner_id")))
                         (error "CENSUS-DEFERRED-OWNER-MISMATCH"))
                       (push (ccl-source-traversal::obj
                               "owner_id" owner "site_id" (ccl-startup-census::dependency-id node)
                               "initializer_id" (ccl-source-traversal::field
                                                   (ccl-source-traversal::field record "function") "function_id"))
                             *initializer-links*)))
                   (push args stack)))))
            ((consp node)
             (unless (gethash node seen)
               (setf (gethash node seen) t)
               (push (cdr node) stack) (push (car node) stack)))))
    (dolist (child (ccl::afunc-inner-functions afunc)) (capture-deferred-links child))))

(defun capture-pass2 (afunc &rest ignored)
  (declare (ignore ignored))
  (unless (and ccl-census-stub::*capture-tag*
               (eq ccl::*target-backend* ccl-census-stub::*backend*))
    (error "CENSUS-CAPTURE-CONTEXT-REQUIRED"))
  (let ((owner ccl::*nx-current-function*))
    (if (and (typep owner 'ccl::afunc) (not (eq owner afunc))
             (not (equal *mode* "first-capture")))
      (progn
        (unless (eq ccl::*load-time-eval-token* ccl::cfasl-load-time-eval-sym)
          (error "CENSUS-INITIALIZER-NOT-DEFERRED"))
        (let* ((ordinal (length *initializers*))
               ;; Close over a distinct ordinal: a constant lambda would be
               ;; shared and would alias all initializer identities.
               (guard (if (and (equal *mode* "alias-initializers") *initializer-guards*)
                        (caar *initializer-guards*)
                        (lambda () (error "CENSUS-INITIALIZER-EXECUTION-FORBIDDEN ~d" ordinal))))
               (record (ccl-source-traversal::obj
                  "owner_id" (ccl-startup-census::dependency-id owner)
                  "function" (ccl-startup-census::function-observation afunc)
                  "deferred_token_matches" :true "executed" :false)))
          (push (cons guard record) *initializer-guards*)
          (push record *initializers*)
          ;; NX1-LOAD-TIME-VALUE embeds the FUNCALL in a deferred literal.
          ;; No initializer is evaluated. The guard is a native fixture
          ;; refusal, not target code; the outer pass 2 still exits before dump.
          (setf (ccl::afunc-lfun afunc) guard)
          (when (equal *mode* "execute-initializer") (funcall guard))
          afunc))
      (progn
        (capture-deferred-links afunc)
        (throw ccl-census-stub::*capture-tag* afunc)))))

(defun batch-flag-expander (form env)
  (declare (ignore env))
  (unless (equal form '(ccl::%get-kernel-global 'ccl::batch-flag))
    (error "CENSUS-KERNEL-GLOBAL-NOT-DESCRIBED: ~s" form))
  (let ((expansion (if (equal *mode* "erase-batch-dependency") 0
                    '(wasm-census-services::startup-batch-flag))))
    (push (ccl-source-traversal::obj
           "source" (ccl-source-traversal::label form)
           "contract" "STARTUP-BATCH-FLAG"
           "expansion" (ccl-source-traversal::label expansion)
           "implementation" "REPLACEMENT_REQUIRED") *expansions*)
    expansion))

(defun with-descriptions (thunk)
  (let* ((arch wasm-census::*census-arch*)
         (table (arch::target-target-macros arch))
         (subtags (arch::target-uvector-subtags arch))
         (old-pass2 (ccl::backend-p2-compile ccl-census-stub::*backend*))
         (name 'ccl::%get-kernel-global))
    (multiple-value-bind (old present) (gethash name table)
      (unwind-protect
        (progn
          (setf (ccl::backend-p2-compile ccl-census-stub::*backend*) #'capture-pass2)
          (setf (arch::target-uvector-subtags arch)
                (unless (equal *mode* "omit-types")
                  '((:basic-stream . 50) (:instance . 114) (:struct . 122)
                    (:istruct . 130) (:min-cl-ivector-subtag . 159)
                    (:array-header . 234) (:vector-header . 242) (:simple-vector . 250))))
          (unless (equal *mode* "omit-batch-macro")
            (setf (gethash name table) #'batch-flag-expander))
          (funcall thunk))
        (setf (arch::target-uvector-subtags arch) subtags)
        (setf (ccl::backend-p2-compile ccl-census-stub::*backend*) old-pass2)
        (if present (setf (gethash name table) old) (remhash name table))))))
