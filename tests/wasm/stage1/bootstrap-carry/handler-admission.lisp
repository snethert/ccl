(defun bootstrap-macroexpand-hook ()
  ;; Validate the native handler macros wherever NX1 encounters them, including
  ;; inside local macros. A lexical macro with the same name is not this API.
  (let ((hook *macroexpand-hook*)
        (bind (macro-function 'handler-bind))
        (case (macro-function 'handler-case)))
    (lambda (expander form environment)
      (when (or (eq expander bind) (eq expander case))
        (dolist (clause (if (eq expander bind) (second form) (cddr form)))
          (unless (and (consp clause) (listp clause))
            (refuse :b-handler-clause))
          (unless (and (eq expander case) (eq (car clause) :no-error))
            (b-condition-mask (car clause)))))
      (funcall hook expander form environment))))
