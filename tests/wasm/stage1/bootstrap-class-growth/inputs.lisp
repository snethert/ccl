(in-package :wasm32-compiler)

(define-condition cpl-left (error) ((payload :initarg :payload :initform 17)))
(define-condition cpl-right (warning) ())
(define-condition cpl-diamond (cpl-left cpl-right) ())
(define-condition cpl-other (error) ())
(define-condition cpl-derived (cpl-diamond)
  ((other :initarg :other :initform 41 :type integer))
  (:default-initargs :payload 43))

(defparameter *cpl-class-names*
  '(condition serious-condition error warning simple-condition simple-error
    type-error cpl-left cpl-right cpl-diamond cpl-other))

(defun cpl-image (name)
  (let ((image (condition-system-image name)))
    (setf (svref image 2) (make-condition name))
    image))

(defun cpl-inputs (name)
  (when (or (member name '(core-condition-eq-vector core-condition-class-initargs core-condition-make-symbol core-condition-make-standard
                          core-condition-make-std core-condition-allocate
                          core-condition-initialize core-condition-shared
                          core-condition-slot-value core-condition-set-slot-value
                          core-condition-slot-boundp core-condition-prepare))
            (eql (search "CORE-CONDITION-READER-" (symbol-name name)) 0)
            (eql (search "CORE-CONDITION-INIT-" (symbol-name name)) 0))
    (return-from cpl-inputs (values nil t)))
  (case name
    (core-condition-create
      (return-from cpl-inputs
        (values (loop for class in '(cpl-left cpl-diamond cpl-derived) append
                  (loop for args in '(nil (:payload 23) (:payload nil) (:payload (1 2)))
                    collect (list (condition-system-image class args)))) t)))
    (core-condition-initargs
      (return-from cpl-inputs
        (values (loop for args in '(nil (:payload 7 :payload 9) (:other 3)
                                   (:payload) (:other 3 :allow-other-keys t))
                      collect (list (condition-system-image 'cpl-left args))) t)))
    (core-condition-implicit-type
      (return-from cpl-inputs
        (values (loop for datum in '(7 :bad "not a list" 1.5d0) collect
                  (list (condition-system-image 'cpl-left) datum)) t)))
    (core-condition-implicit-float
      (return-from cpl-inputs
        (values (list (list (condition-system-image 'cpl-left) 1000.0d0 0.0d0 -1.0d0)) t)))
    (core-condition-implicit-divide
      (return-from cpl-inputs
        (values (loop for datum in '(0 7 -11) collect
                  (list (condition-system-image 'cpl-left) datum 0)) t)))
    (core-condition-implicit-undefined
      ;; The target retains the base-class boundary for FUNCALL. Initialize
      ;; native's more specific class before the graph snapshot, so its lazy
      ;; keyword metadata is not mistaken for a target mutation requirement.
      (make-condition 'ccl::undefined-function-call :name nil :function-arguments nil)
      (return-from cpl-inputs
        (values (list (list (condition-system-image 'cpl-left) (make-symbol "UNBOUND-CELL"))) t)))
    (core-condition-table-grow
      (return-from cpl-inputs
        (values (loop for count in '(1500 3500) collect
                  (let ((image (condition-system-image 'cpl-left)))
                    (setf (svref image 10)
                          (loop for i below count collect (make-symbol (format nil "NEW-CLASS-~d" i))))
                    (list image))) t)))
    ((core-condition-implicit-unbound core-condition-table-remove core-condition-remove-read-only core-condition-own-table core-condition-table-clear core-condition-table-store core-condition-new-cell core-condition-rebuild-cells core-condition-table-read-only core-condition-signal-string core-condition-signal-symbol core-condition-spread core-condition-slots core-condition-unlisted core-condition-cerror core-condition-indirect core-condition-class-cell)
      (return-from cpl-inputs (values (list (list (condition-system-image 'cpl-left))) t))))
  (when (eql (search "CORE-CPL-" (symbol-name name)) 0)
    (values (loop for class in '(cpl-diamond cpl-left cpl-right cpl-other)
                  collect (list (cpl-image class))) t)))

(defvar *condition-system-methods* nil)
(defvar *condition-hash-vectors* (make-hash-table :test #'eq))
(defvar *condition-initforms* nil)

(defun condition-system-protocol ()
  (let ((gfs (generic-protocol-image)))
    (setq *condition-system-methods* nil)
    (dolist (spec *condition-method-specs*)
      (destructuring-bind (name classes entry) spec
        (let* ((gf (fdefinition name))
               (method (find-method gf nil (mapcar #'find-class classes))))
          (pushnew gf gfs)
          (push method *condition-system-methods*)
          (setf (gethash gf *generic-bindings*) (ccl::maybe-setf-function-name name)
                (gethash (ccl::%method-function method) *accessor-function-names*) entry))))
    (dolist (spec *condition-reader-specs*)
      (destructuring-bind (name class slot) spec
        (declare (ignore slot))
        (let* ((gf (fdefinition name))
               (method (find-method gf nil (list (find-class class))))
               (entry (intern (concatenate 'string "CORE-CONDITION-READER-" (symbol-name name))
                              :wasm32-compiler)))
          (pushnew gf gfs)
          (push method *condition-system-methods*)
          (setf (gethash gf *generic-bindings*) (ccl::maybe-setf-function-name name)
                (gethash (ccl::%method-function method) *accessor-function-names*) entry))))
    gfs))

(defun condition-system-image (name &optional args)
  (let* ((base (generic-image nil))
         (protocol (condition-system-protocol))
         (classes (make-hash-table :test #'eq))
         (image (concatenate 'vector base (vector name args protocol nil nil nil nil))))
    ;; Snapshot actual class cells by native identity. No manufactured class
    ;; catalogue or name-only join: the hash keys are package-qualified symbols.
    (maphash (lambda (name cell)
               (let ((class (ccl::class-cell-class cell)))
                 (when (and class (ccl::class-finalized-p class))
                   (setf (gethash name classes) cell))))
             ccl::%find-classes%)
    (setf (gethash (ccl::nhash.vector classes) *condition-hash-vectors*) classes)
    (setf (svref image 1) nil
          (svref image 2) (make-condition 'cpl-diamond)
          (svref image 3) classes
          (svref image 12) (list ccl::*initialization-invalidation-alist*
                                ccl::*standard-class-wrapper*
                                ccl::*standard-effective-slot-definition-class-wrapper*
                                ccl::*error-format-strings*))
    (setf (svref image 11)
          (sort (loop for name being the hash-keys of classes using (hash-value cell)
                      collect (cons name (ccl::class-cell-class cell)))
                #'string< :key (lambda (pair) (format nil "~s" (car pair)))))
    (setf (gethash image *generic-graphs*) t)
    image))

;;; The owner constructor is new target code. Its reference is an ordinary
;;; native EQ table; it does not stand in for an original CCL definition.
(defun ccl::%wasm-make-class-table (size)
  (make-hash-table :test #'eq :size size))
