(in-package "CCL")

;;; The portable definition is the same one used by x8632-array.lisp.
(defun %init-misc (val uvector)
  (dotimes (i (uvsize uvector) uvector)
    (setf (uvref uvector i) val)))

;;; Numeric dispatch uses canonical numeric type names. Other type specifiers
;;; still need the full type system and must not be silently accepted here.
(defun %wasm-numeric-type-p (value typespec)
  (case typespec
    (number (typep value 'number))
    (real (typep value 'real))
    (rational (typep value 'rational))
    (integer (typep value 'integer))
    (fixnum (typep value 'fixnum))
    (bignum (typep value 'bignum))
    (ratio (typep value 'ratio))
    (float (typep value 'float))
    ((short-float single-float) (typep value 'single-float))
    ((long-float double-float) (typep value 'double-float))
    (complex (typep value 'complex))
    (t (error "This numeric restart type is not supported."))))

(defun %wasm-require-numeric-type (value typespec)
  (loop
    (when (%wasm-numeric-type-p value typespec)
      (return value))
    (setq value (%wasm-numeric-type-restart value typespec))))

(defun %wasm-numeric-type-restart (value typespec)
  (restart-case (error 'type-error :datum value :expected-type typespec)
    (use-value (newval)
      (%wasm-require-numeric-type newval typespec))))

(defun %wasm-kernel-restart (error-type args)
  (dolist (entry *kernel-restarts*)
    (when (eq (car entry) error-type)
      ;; There is no native machine frame pointer on this target.
      (return-from %wasm-kernel-restart (apply (cdr entry) nil args))))
  (if (and (eql error-type $xwrongtype) (= (length args) 2))
    (%wasm-numeric-type-restart (car args) (cadr args))
    (error "This kernel restart is not supported.")))

;;; $XTMINPS in l0-error.lisp. Preserve the native condition and its payload.
(defun %wasm-too-many-arguments ()
  (error "Too many arguments."))
