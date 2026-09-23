(in-package :wasm32-compiler)

(defun validation-class-error (image)
  (core-condition-prepare image)
  (handler-case (error "plain")
    (error () :caught)))

(defun validation-class-type-error (image)
  (core-condition-prepare image)
  (handler-case (ccl::require-type (svref image 3) 'string)
    (type-error () :refused)))

(defun validation-class-capacity (image)
  (core-condition-prepare image)
  ;; The target's fixed ceiling is an explicit boundary, not native's limit.
  (handler-case (progn
                 #+wasm32-target (ccl::%wasm-make-class-table 16385)
                 #-wasm32-target (error 'type-error :datum 16385
                                       :expected-type '(integer 4 16384))
                 :made)
    (type-error () :refused)))

(defun validation-class-allocate (image)
  (core-condition-prepare image)
  (let ((table (ccl::%wasm-make-class-table 16384)))
    (core-collect)
    (not (null table))))
