(in-package :ccl)

;;; Lisp counterpart of x8632's CLASS-OF LAP entry. The image supplies the
;;; same typecode-indexed class table, containing classes or discriminator
;;; functions. No host class or host typecode participates in target lookup.
(defun class-of (object)
  (let ((entry (%svref *class-table*
                       (if (characterp object) target::subtag-character (typecode object)))))
    (cond ((null entry) (no-class-error object))
          ((functionp entry) (funcall entry object))
          (t entry))))

(defun %class-of-instance (instance)
  (%wrapper-class (instance.class-wrapper instance)))

(defun %wasm-class-of-list (object)
  (if object *cons-class* *null-class*))

(defun macptrp (object)
  (= (typecode object) target::subtag-macptr))

;;; EQL-SPECIALIZER's standard reader. Its OBJECT slot follows DIRECT-METHODS;
;;; the native class-slot inventory qualifies this index with the image.
(defun %wasm-eql-specializer-reader (&method context specializer)
  (declare (ignore context))
  (%slot-ref (instance-slots specializer) 2))

;;; Unlike the native assembly dcode, D1's entry is an ordinary closure.
;;; Applicability and combination are still the original Lisp algorithms.
;;; Recomputing from the current method list also avoids a stale dcode after
;;; removing the final method. A cache can be added without changing this ABI.
(defun %wasm-standard-generic-call (gf args)
  (let* ((bits (inner-lfun-bits gf))
         (required (ldb $lfbits-numreq bits))
         (optional (ldb $lfbits-numopt bits))
         (count (length args)))
    (when (< count required) (signal-program-error "Too few args to ~s" gf))
    (unless (or (<= count (+ required optional))
                (logbitp $lfbits-rest-bit bits)
                (logbitp $lfbits-restv-bit bits)
                (logbitp $lfbits-keys-bit bits))
      (signal-program-error "Too many args to ~s" gf))
    (let* ((methods (%compute-applicable-methods* gf args))
           (combination (%gf-method-combination gf)))
      (unless methods
        (return-from %wasm-standard-generic-call (apply #'no-applicable-method gf args)))
      (unless (eq combination *standard-method-combination*)
        (return-from %wasm-standard-generic-call
          (apply (compute-effective-method-function gf combination methods) args)))
      (let* ((keywords (compute-allowable-keywords-vector gf methods))
             (method-list (compute-method-list methods)))
        (unless method-list
          (return-from %wasm-standard-generic-call (no-applicable-primary-method gf methods)))
        (when (atom method-list) (setq method-list (list method-list)))
        (let* ((key-index (+ required optional))
               (key-info (when keywords (vector key-index keywords gf)))
               (context (vector gf methods key-info
                                (when keywords #'x-%%check-keywords) method-list))
               (combined (lambda (&rest args)
                           (%%cnm-with-args-combined-method-dcode context args))))
          (if keywords
            (%%check-keywords (vector key-index keywords combined gf) args)
            (apply combined args)))))))

(defun compute-dcode (gf &optional dt)
  (setq dt (or dt (%gf-dispatch-table gf)))
  (clear-gf-dispatch-table dt)
  (setf (%gf-dispatch-table-argnum dt) -1)
  (setf (gf.dcode gf)
        (lambda (&rest args) (%wasm-standard-generic-call gf args))))

;;; The native EQUAL entry is LAP. Retain its Lisp calls for recursive conses
;;; and non-EQL uvectors; EQL remains the shared numeric identity operation.
(defun equal (x y)
  (cond ((eq x y) t)
        ((consp x) (and (consp y) (cons-equal x y)))
        ((and (miscobjp x) (miscobjp y))
         (or (eql x y) (hairy-equal x y)))))

(defun false (&rest args)
  (declare (ignore args))
  nil)
