(in-package :wasm32-compiler)

(defun core-controls (out)
  (let ((rows nil))
    (flet ((expect-refusal (name form result reason)
             (let ((actual
                     (handler-case (progn (core-check-body form result) :admitted)
                       (unsupported-wasm32-code (c) (unsupported-operation c)))))
               (assert (eq actual reason))
               (push (list name actual) rows))))
      (let ((*core-native-forms* (make-hash-table :test #'eq)))
        (setf (gethash 'core-empty *core-native-forms*) '(defun core-empty (x) (consp x)))
        (dolist (row '((:empty-target (defun core-empty (x) "Documentation.") :bootstrap-empty-target-body)
                       (:self-call (defun core-self (x) (core-self x)) :bootstrap-self-only-body)))
          (destructuring-bind (name form reason) row
            (let* ((wire (string-downcase (symbol-name name)))
                   (result (call-with-target (lambda () (compile-bootstrap-form form wire nil)))))
              (with-open-file (s (concatenate 'string out wire ".refused-wat")
                                 :direction :output :if-exists :error)
                (write-string (getf result :wat) s))
              (expect-refusal name form result reason))))
        (expect-refusal :aliased-self-call '(defun core-self (x) (core-self x))
                        '(:dependencies (core-other)) :bootstrap-self-only-body)
        (core-check-body '(defun core-empty (x) nil) nil)
        (core-check-body '(defun core-self (x) (core-self x)) '(:dependencies nil :self-call nil))))
    (dolist (row '((:native-ffi (defun refused () (ccl::ff-call 0 :void)) :native-ffi-excluded)
                   (:function-immediate-read (defun refused (f) (ccl::nth-immediate f 1)) :function-immediate-layout)
                   (:function-immediate-write (defun refused (f v) (ccl::set-nth-immediate f 1 v)) :function-immediate-layout)
                   (:escaping-lexpr (defun refused (ccl::&lexpr args) (lambda () (ccl::%lexpr-count args))) :b-local-owner)
                   (:unknown-handler-bind
                    (defun refused () (handler-bind ((file-error #'identity)) 7)) :b-condition-type)
                   (:unknown-handler-case
                    (defun refused () (handler-case 7 (file-error () 8))) :b-condition-type)
                   (:macro-introduced-handler
                    (defun refused () (macrolet ((check () '(handler-bind ((file-error #'identity)) 7)))
                                        (check))) :b-condition-type)
                   (:compound-handler-type
                    (defun refused () (handler-bind (((or type-error file-error) #'identity)) 7)) :b-condition-type)
                   (:signal-spread (defun refused (args) (apply #'signal args)) :bootstrap-signal-spread)
                   (:error-spread (defun refused (args) (apply #'error args)) :bootstrap-signal-spread)
                   (:signal-no-arguments (defun refused () (signal)) :bootstrap-signal-arity)
                   (:unknown-condition-class (defun refused () (error 'warning)) :bootstrap-condition-class)
                   (:odd-condition-initargs (defun refused () (error 'type-error :datum)) :bootstrap-condition-initargs)
                   (:unknown-condition-initarg (defun refused () (error 'type-error :unknown 7)) :bootstrap-condition-initarg)
                   (:condition-reader-arity (defun refused () (type-error-datum)) :bootstrap-condition-reader-arity)
                   (:bit-vector-kind (defun refused (x) (declare (type (simple-array bit (*)) x)) (aref x 0)) :bootstrap-array-kind)))
      (destructuring-bind (name form expected) row
        (let ((actual (handler-case
                          (progn (call-with-target (lambda () (compile-bootstrap-form form "refusal" nil))) :admitted)
                        (unsupported-wasm32-code (c) (unsupported-operation c)))))
          (unless (eq actual expected) (error "~s: wanted ~s, got ~s" name expected actual))
          (push (list name actual) rows))))
    (dolist (form '((defun admitted ()
                     (macrolet ((handler-bind (&rest ignored) (declare (ignore ignored)) 7))
                       (handler-bind ((file-error #'identity)) 9)))
                    (defun admitted ()
                      (macrolet ((handler-case (&rest ignored) (declare (ignore ignored)) 7))
                        (handler-case 9 (file-error () 8))))
                    (defun admitted () '(handler-bind ((file-error #'identity)) 9))))
      (call-with-target (lambda () (compile-bootstrap-form form "admitted" nil))))
    ;; The omission admits a real, unsupported condition class. This checks
    ;; that the admission rule, rather than a later emitter refusal, decides.
    (let ((guard (fdefinition 'bootstrap-macroexpand-hook)))
      (unwind-protect
          (progn
            (setf (fdefinition 'bootstrap-macroexpand-hook)
                  (lambda () *macroexpand-hook*))
            (call-with-target
             (lambda ()
               (compile-bootstrap-form
                '(defun admitted () (handler-bind ((file-error #'identity)) 7))
                "omitted_handler_guard" nil)))
            (push '(:handler-guard-omission :admitted) rows))
        (setf (fdefinition 'bootstrap-macroexpand-hook) guard)))
    (with-open-file (s (concatenate 'string out "measure-controls.sexp")
                       :direction :output :if-exists :error)
      (prin1 (nreverse rows) s))))
