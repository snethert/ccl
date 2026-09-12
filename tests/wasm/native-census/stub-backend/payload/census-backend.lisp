;;; Census registration only: pass 2 captures IR and exits; it cannot emit code.
(defpackage "CCL-CENSUS-STUB" (:use "CL"))
(in-package "CCL-CENSUS-STUB")
(defvar *capture-tag* nil)
(defvar *backend*
  (ccl::make-backend
   :name :wasm32-census :num-arg-regs 0
   :target-arch-name :wasm32-census :target-arch wasm-census::*census-arch*
   ;; Unused U1 CPU/OS bit patterns, local to this observation fixture. No ABI allocation.
   :target-platform #x27 :target-os :wasm-census
   :target-specific-features '(:wasm-target :wasm32-target :32-bit-target :little-endian-target)
   :target-fasl-pathname (make-pathname :type "census-no-code")
   :p2-dispatch #() :p2-compile 'capture-pass2
   :p2-vinsn-templates (make-hash-table :test #'eq)
   :target-foreign-type-data
   (ccl::make-ftd :interface-package-name "WASM-CENSUS-OS" :attributes '(:bits-per-word 32))))

(defun capture-pass2 (afunc &rest ignored)
  (declare (ignore ignored))
  (unless (and *capture-tag* (eq ccl::*target-backend* *backend*))
    (error "Census pass 2 requires an explicit capture context"))
  (throw *capture-tag* afunc))

(when (and (ccl::find-backend :wasm32-census)
           (not (eq *backend* (ccl::find-backend :wasm32-census))))
  (error "Conflicting census backend registration"))
(pushnew *backend* ccl::*known-backends* :key #'ccl::backend-name)

(defun with-target-state (thunk)
  (let* ((ccl::*target-backend* *backend*)
         (ccl::*fasl-target* :wasm32-census)
         (*features* (ccl::setup-target-features *backend* *features*)))
    (ccl::with-cross-compilation-target (:wasm32-census)
      (funcall thunk))))

(defun capture-lambda (form name)
  (let* ((*capture-tag* (gensym "CENSUS-PASS2"))
         (answer (catch *capture-tag*
                   (ccl::compile-named-function form :name name :target :wasm32-census
                                                :policy ccl::*default-compiler-policy*)
                   (error "Census compilation returned executable output"))))
    (unless (typep answer 'ccl::afunc) (error "Pass 2 did not capture a compiler function"))
    answer))
(provide "WASM-CENSUS-BACKEND")
