(in-package :wasm32-compiler)

(let ((rows nil))
  ;; NIL has a dedicated acode operator and remains an ordinary, unresolved
  ;; MAKE-CONDITION call. It cannot enter this constant-symbol constructor arm.
  (dolist (row '((:nil-class (make-condition nil) :admitted)
                 (:unknown-class (make-condition 'reader-error) :bootstrap-condition-class)
                 (:odd-initargs (make-condition 'type-error :datum) :bootstrap-condition-initargs)
                 (:unknown-initarg (make-condition 'type-error :unknown 7) :bootstrap-condition-initarg)
                 (:association-class (ccl::condition-arg 'reader-error (list :datum 7) 'simple-error)
                                     :bootstrap-condition-class)))
    (destructuring-bind (name body expected) row
      (let ((actual (handler-case
                        (progn (call-with-target
                                 (lambda () (compile-bootstrap-form `(defun probe () ,body) "gcd_control" nil)))
                               :admitted)
                      (unsupported-wasm32-code (c) (unsupported-operation c)))))
        (unless (eq actual expected) (error "~s: wanted ~s, got ~s" name expected actual))
        (push (list name actual) rows))))
  (with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "gcd-controls.sexp")
                     :direction :output :if-exists :error)
    (prin1 (nreverse rows) s)))
