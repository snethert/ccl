(in-package :wasm32-compiler)

(defvar *accessor-function-names* (make-hash-table :test #'eq))

(defparameter *condition-method-specs*
  '((ccl::class-slot-initargs (ccl::slots-class) core-condition-class-initargs)
    (make-instance (symbol) core-condition-make-symbol)
    (make-instance (standard-class) core-condition-make-standard)
    (make-instance (ccl::std-class) core-condition-make-std)
    (allocate-instance (standard-class) core-condition-allocate)
    (initialize-instance (standard-object) core-condition-initialize)
    (shared-initialize (standard-object t) core-condition-shared)
    (ccl::slot-value-using-class (standard-class t ccl::standard-effective-slot-definition)
      core-condition-slot-value)
    ((setf ccl::slot-value-using-class) (t standard-class t ccl::standard-effective-slot-definition)
      core-condition-set-slot-value)
    (ccl::slot-boundp-using-class (standard-class t ccl::standard-effective-slot-definition)
      core-condition-slot-boundp)))

;;; These readers are the ordinary MOP accessors that CCL synthesizes from
;;; DEFCLASS. Their names and locations come from the native slot definitions.
;;; Reading via SLOT-VALUE preserves lookup on the actual class of the object.
(defparameter *condition-reader-specs*
  '((ccl:class-slots ccl::class ccl::slots)
    (ccl::slot-definition-predicate ccl::effective-slot-definition ccl::type-predicate)
    (ccl::slot-definition-initargs ccl::slot-definition ccl::initargs)
    (ccl::slot-definition-initfunction ccl::slot-definition ccl::initfunction)
    (ccl::slot-definition-name ccl::slot-definition ccl::name)
    (ccl::slot-definition-type ccl::slot-definition ccl::type)
    (cell-error-name cell-error ccl::name)
    (arithmetic-error-operation arithmetic-error ccl::operation)
    (arithmetic-error-operands arithmetic-error ccl::operands)
    (type-error-datum type-error ccl::datum)
    (type-error-expected-type type-error ccl::expected-type)
    (simple-condition-format-control simple-condition ccl::format-control)
    (simple-condition-format-arguments simple-condition ccl::format-arguments)))

(defun condition-system-method-forms ()
  (let ((*package* (find-package :ccl)) (forms nil))
    (dolist (file '("ccl:level-1;l1-clos-boot.lisp" "ccl:level-1;l1-clos.lisp" "ccl:level-1;l1-streams.lisp"))
      (with-open-file (stream file)
        (loop for form = (read stream nil :eof) until (eq form :eof) do
          (when (and (consp form) (eq (car form) 'defmethod))
            (let* ((tail (cddr form))
                   (qualifiers (loop while (and tail (atom (car tail))) collect (pop tail)))
                   (specializers
                     (loop for arg in (car tail) until (member arg lambda-list-keywords)
                           collect (if (consp arg) (second arg) t)))
                   (spec (find-if (lambda (spec)
                                   (and (equal (first spec) (second form))
                                        (equal (second spec) specializers)
                                        (equal (fourth spec) qualifiers)))
                                 *condition-method-specs*)))
              (when spec
                (let ((function (ccl::parse-defmethod (second form) (cddr form) nil)))
                  (push `(defun ,(third spec) ,@(cdr (third function))) forms))))))))
    (assert (= (length forms) (length *condition-method-specs*)))
    (dolist (spec *condition-reader-specs*)
      (destructuring-bind (name class slot) spec
        (let* ((entry (intern (concatenate 'string "CORE-CONDITION-READER-" (symbol-name name))
                              :wasm32-compiler))
               (function (ccl::parse-defmethod name
                           `(((object ,class)) (slot-value object ',slot)) nil)))
          (push `(defun ,entry ,@(cdr (third function))) forms))))
    (nreverse forms)))

(defun condition-system-support-forms ()
  (let ((forms nil) (index 0) (seen (make-hash-table :test #'eq)))
    (labels ((entry (function body)
               (when (and function (not (gethash function seen)))
                 (let ((name (intern (format nil "CORE-CONDITION-INIT-~d" (incf index))
                                     :wasm32-compiler)))
                   (setf (gethash function seen) t
                         (gethash function *accessor-function-names*) name)
                   (push `(defun ,name ,@body) forms)))))
      (dolist (class (sort (loop for cell being the hash-values of ccl::%find-classes%
                                for class = (ccl::class-cell-class cell)
                                when (and class (ccl::class-finalized-p class)
                                          (or (subtypep (class-name class) 'condition)
                                              (member (class-name class)
                                                '(class standard-class built-in-class ccl::funcallable-standard-class
                                                  ccl::funcallable-standard-object generic-function standard-generic-function
                                                  ccl::standard-effective-slot-definition
                                                  ccl::slot-definition ccl::effective-slot-definition))))
                                  collect class)
                           #'string< :key (lambda (c) (format nil "~s" (class-name c)))))
        (dolist (slot (ccl:class-slots class))
          (entry (ccl:slot-definition-initfunction slot)
                 `(() ,(ccl:slot-definition-initform slot)))
          (entry (ccl::slot-definition-predicate slot)
                 `((value) (typep value ',(ccl:slot-definition-type slot)))))
        (dolist (entry (ccl::%class-default-initargs class))
          (entry (third entry) `(() ,(second entry))))))
    (nreverse forms)))

(defparameter *condition-system-callers*
  '(core-condition-table-grow core-condition-table-remove core-condition-remove-read-only core-condition-own-table core-condition-table-clear core-condition-implicit-type core-condition-implicit-divide core-condition-implicit-unbound core-condition-implicit-undefined core-condition-implicit-float core-condition-table-store core-condition-new-cell core-condition-rebuild-cells core-condition-table-read-only core-condition-create core-condition-signal-string core-condition-signal-symbol
    core-condition-spread core-condition-initargs core-condition-slots
    core-condition-unlisted core-condition-cerror core-condition-indirect
    core-condition-class-cell))

(defun condition-system-entry-p (name)
  (or (member name *condition-system-callers*)
      (member name '(core-condition-prepare core-condition-eq-vector))
      (find name *condition-method-specs* :key #'third)
      (eql (search "CORE-CONDITION-INIT-" (symbol-name name)) 0)
      (eql (search "CORE-CONDITION-READER-" (symbol-name name)) 0)))

(load (merge-pathnames "ready-clos-methods.lisp" *load-pathname*))
