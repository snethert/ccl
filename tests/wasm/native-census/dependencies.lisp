;;; Add dependency identities to the reviewed observer; never mutate compiler IR.
(in-package :ccl-startup-census)

(defvar *dependency-base-observation* (symbol-function 'function-observation))
(defvar *dependency-base-snapshot* (symbol-function 'snapshot))
(defvar *dependency-base-observe* (symbol-function 'observe))
(defvar *dependency-base-finish* (symbol-function 'finish))
(defvar *dependency-identities* (make-hash-table :test #'eq :weak :key))
(defvar *dependency-counter* 0)
(defvar *dependency-lock* (ccl:make-lock "census identities"))
(defvar *dependency-binding-lock* (ccl:make-lock "census binding checkpoints"))
(defvar *dependency-bindings* (make-hash-table :test #'equal))
(defvar *dependency-source* nil)

(defun dependency-id (value)
  ;; Compiler object identity, not printed names or addresses. The keys are weak
  ;; so collecting old compiler objects is unaffected by keeping this map.
  (ccl:with-lock-grabbed (*dependency-lock*)
    (or (gethash value *dependency-identities*)
        (setf (gethash value *dependency-identities*) (incf *dependency-counter*)))))

(defun dependency-field (record name)
  (loop for (key value) on (cdr record) by #'cddr
        when (string= key name) return value))

(defun dependency-function (afunc)
  (object "kind" "function" "id" (dependency-id afunc)
          "name" (label-of (ccl::afunc-name afunc))))

(defun dependency-global (name)
  (multiple-value-bind (valid canonical) (ccl::valid-function-name-p name)
    (when valid
      (object "kind" "global-binding" "name" (label-of canonical)))))

(defun dependency-callee (node)
  (let ((seen (make-hash-table :test #'eq)))
    (loop
      (unless (ccl::acode-p node)
        (return (object "category" "unrecognized-callee" "targets" nil)))
      (when (gethash node seen)
        (return (object "category" "cyclic-callee-form" "targets" nil)))
      (setf (gethash node seen) t)
      (let* ((op (ccl::acode-operator-name (ccl::acode-operator node)))
             (args (ccl::acode-operands node)) (value (car args)))
        (case op
          ((ccl::typed-form ccl::type-asserted-form) (setf node (second args)))
          ((ccl::simple-function ccl::closed-function)
           (return (if (typep value 'ccl::afunc)
                     (object "category" "lexical-function-value" "targets" (list (dependency-function value)))
                     (object "category" "unrecognized-function-value" "targets" nil))))
          ((ccl::immediate ccl::%function)
           (let ((global (dependency-global value)))
             (return (object "category" (if global "global-binding" "literal-without-binding")
                             "targets" (if global (list global) nil)))))
          ((ccl::lexical-reference ccl::inherited-arg)
           (return (if (typep value 'ccl::var)
                     (let ((root (ccl::nx-root-var value)))
                       (object "category" "function-variable" "targets" nil
                               "variable_id" (dependency-id root)
                               "variable_name" (label-of (ccl::var-name root))))
                     (object "category" "unrecognized-variable" "targets" nil))))
          (t (return (object "category" "computed-callee" "targets" nil
                             "callee_operator" (label-of op)))))))))

(defun dependency-call (node afunc)
  (let* ((op (ccl::acode-operator-name (ccl::acode-operator node)))
         (value (car (ccl::acode-operands node))))
    (case op
      (ccl::self-call
       ;; nx0.lisp:2076: self-call's first operand is the argument list.
       (object "category" "self" "targets" (list (dependency-function afunc))))
      (ccl::lexical-function-call
       ;; nx0.lisp:2418: the callee is the actual afunc object.
       (unless (typep value 'ccl::afunc) (error "Invalid lexical callee"))
       (object "category" "lexical" "targets" (list (dependency-function value))))
      (ccl::builtin-call
       ;; arch.lisp:225: builtin indices address the evaluated native table.
       (unless (and (ccl::acode-p value)
                    (eq (ccl::acode-operator-name (ccl::acode-operator value)) 'ccl::fixnum))
         (error "Invalid builtin operand"))
       (let* ((index (car (ccl::acode-operands value)))
              (name (elt ccl::%builtin-functions% index)))
         (object "category" "builtin" "builtin_index" index
                 "targets" (list (or (dependency-global name) (error "Invalid builtin binding"))))))
      (t (dependency-callee value)))))

(defun function-observation (afunc)
  (let* ((record (funcall *dependency-base-observation* afunc))
         (calls (dependency-field record "calls"))
         (seen (make-hash-table :test #'eq))
         (stack (list (ccl::afunc-acode afunc))) (references nil))
    ;; Same acode traversal order as the base observer, checked call by call.
    (loop while stack for node = (pop stack) do
      (cond
        ((ccl::acode-p node)
         (unless (gethash node seen)
           (setf (gethash node seen) t)
           (let* ((op (ccl::acode-operator-name (ccl::acode-operator node)))
                  (operands (ccl::acode-operands node)))
             (when (member op '(ccl::call ccl::builtin-call ccl::lexical-function-call ccl::self-call))
               (let ((call (pop calls)))
                 (unless (and call (string= (dependency-field call "operator") (label-of op)))
                   (error "Base/dependency traversal differs"))
                 (nconc call (list "site_id" (dependency-id node)
                                   "dependency" (dependency-call node afunc)))))
             (when (member op '(ccl::simple-function ccl::closed-function ccl::%function))
               (push (object "site_id" (dependency-id node) "dependency" (dependency-callee node)) references))
             (unless (member op '(ccl::immediate ccl::fixnum ccl::nil ccl::t))
               (push operands stack)))))
        ((consp node)
         (unless (gethash node seen)
           (setf (gethash node seen) t)
           (push (cdr node) stack) (push (car node) stack)))))
    (when calls (error "Base call records remain unmatched"))
    (nconc record
           (list "function_id" (dependency-id afunc)
                 "parent_id" (if (ccl::afunc-parent afunc) (dependency-id (ccl::afunc-parent afunc)) :null)
                 "variables" (loop for var in (ccl::afunc-vars afunc) for index from 0
                                   collect (object "id" (dependency-id (ccl::nx-root-var var))
                                                   "name" (label-of (ccl::var-name var)) "ordinal" index))
                 "function_references" (nreverse references)))))

(defun snapshot ()
  (nconc (funcall *dependency-base-snapshot*)
         (list "dependency_format" 1
               "builtin_bindings" (loop for name across ccl::%builtin-functions%
                                        for index from 0 collect
                                        (object "index" index "name" (label-of name)))
               "definition_format" 1
               "binding_scope" "Native host samples; not every installation or cross-dumped target binding")))

(defun dependency-binding-state (name)
  (let ((bound (fboundp name)) (macro (and (symbolp name) (macro-function name))))
    (object "role" (cond (macro "macro")
                         ((and (symbolp name) (special-operator-p name)) "special-operator")
                         ((functionp bound) "function") (bound "other-bound") (t "unbound"))
            "function_id" (if (functionp bound) (dependency-id bound) :null)
            "macro_id" (if macro (dependency-id macro) :null))))

(defun dependency-sample-binding (name reason)
  (let* ((old (gethash name *dependency-bindings*))
         (state (dependency-binding-state name)))
    (unless (and old (equal (car old) state))
      (emit "binding-checkpoint"
            (object "name" (label-of name) "reason" reason
                    "previous_sample_sequence" (if old (cdr old) :null)
                    "previous" (if old (car old) :null) "state" state
                    "scope" "Observed native host change within a sample interval; installation site not inferred")))
    (setf (gethash name *dependency-bindings*) (cons state *sequence*))))

(defun dependency-checkpoint (reason)
  ;; Once per source transition or explicit checkpoint, never once per IR node.
  (maphash (lambda (name old) (declare (ignore old))
             (dependency-sample-binding name reason)) *dependency-bindings*))

(defun dependency-quoted-name (form)
  (when (and (consp form) (eq (car form) 'quote)) (cadr form)))

(defun dependency-definition-name (form)
  (when (and (consp form) (member (car form) '(ccl::nfunction ccl::qlfun function)))
    (cadr form)))

(defun dependency-definition-forms (form phase)
  ;; These are source declarations, not executed definitions. Do not search
  ;; quotes, function bodies, arbitrary argument lists or local macro bodies.
  ;; The compiler's own macroexpand hook supplies expanded top-level forms.
  (let ((stack (list (list form nil))) (names nil))
    (labels ((record (name role operator context &optional implementation)
               (let* ((global (and name (dependency-global name)))
                      (canonical (and global (nth-value 1 (ccl::valid-function-name-p name)))))
                 (emit "definition-form"
                       (object "name" (if global (dependency-field global "name") :null)
                               "role" role "operator" (label-of operator) "phase" phase
                               "contexts" context "implementation_name" (if implementation (label-of implementation) :null)
                               "resolution" (if global "literal-binding-name" "unresolved-definition-name")))
                 (when global
                   (unless (gethash canonical *dependency-bindings*)
                     (dependency-sample-binding canonical "first-declaration"))
                   (pushnew canonical names :test #'equal)))))
      (loop while stack for item = (pop stack) for node = (first item) for context = (second item) do
        (when (consp node)
          (let ((op (car node)))
            (case op
              ((progn locally)
               (dolist (child (reverse (cdr node))) (push (list child context) stack)))
              (eval-when
               (dolist (child (reverse (cddr node)))
                 (push (list child (append context (list (label-of (cadr node))))) stack)))
              ((defun defmacro defgeneric)
               (record (cadr node) (if (eq op 'defmacro) "macro" "function") op context))
              (defmethod (record (cadr node) "method" op context))
              ((ccl::%defun ccl::%macro)
               (record (dependency-definition-name (cadr node))
                       (if (eq op 'ccl::%macro) "macro" "function") op context))
              ((ccl::%fhave ccl::fset ccl::fset-symbol)
               (record (dependency-quoted-name (cadr node)) "function-binding-write" op context
                       (dependency-definition-name (caddr node))))
              (setf
               (loop for (place value) on (cdr node) by #'cddr do
                 (when (and (consp place) (member (car place) '(symbol-function fdefinition macro-function)))
                   (record (dependency-quoted-name (cadr place))
                           (if (eq (car place) 'macro-function) "macro-binding-write" "function-binding-write")
                           op context (dependency-definition-name value)))))))))
      names)))

(defun observe (phase value)
  (unless *busy*
    (funcall *dependency-base-observe* phase value)
    (let ((*busy* t) (*gensym-counter* *gensym-counter*))
      (when (member phase '(:read :macroexpand :compile-initializer-enter :compile-initializer-return))
        (ccl:with-lock-grabbed (*dependency-binding-lock*)
          (when (and (eq phase :read) (not (equal *compile-file-truename* *dependency-source*)))
            (dependency-checkpoint "source-transition")
            (setf *dependency-source* *compile-file-truename*))
          (let ((names (dependency-definition-forms (if (eq phase :macroexpand) (second value) value)
                                                    (string-downcase (symbol-name phase)))))
            (when (member phase '(:compile-initializer-enter :compile-initializer-return))
              (dolist (name names) (dependency-sample-binding name (string-downcase (symbol-name phase)))))))))))

(defun checkpoint (reason)
  ;; Explicit harness checkpoints can bracket loads without changing CCL's
  ;; loader or fset. Transient changes between samples remain unobserved.
  (let ((*busy* t) (*gensym-counter* *gensym-counter*))
    (ccl:with-lock-grabbed (*dependency-binding-lock*) (dependency-checkpoint reason))))

(defun finish ()
  (checkpoint "observation-finish")
  (funcall *dependency-base-finish*))
