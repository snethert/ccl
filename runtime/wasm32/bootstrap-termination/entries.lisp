;; These are replacement definitions for the selected Stage 1 image, not native
;; finalization semantics. The fixture keeps native CCL's functions untouched.
;; Package-qualified production bindings are enumerated in bindings.json.
(("termination_register"
  (lambda (object &optional callback)
    (declare (special termination_unavailable))
    (error termination_unavailable)))
 ("termination_cancel" (lambda (object &optional callback) nil))
 ("termination_lookup" (lambda (object) nil))
 ("termination_drain" (lambda () nil))
 ("termination_automatic"
  (lambda ()
    (declare (special automatic_termination_enabled termination_unavailable))
    (if automatic_termination_enabled (error termination_unavailable) nil)))
 ("termination_named"
  (lambda (object callback done)
    (handler-case
      (unwind-protect (termination_register object callback) (rplaca done 611))
      (simple-error (c) (values 701 (car done)))
      (error (c) 702))))
 ("termination_default"
  (lambda (object done)
    (handler-case
      (unwind-protect (termination_register object) (rplaca done 612))
      (simple-error (c) (values 701 (car done))))))
 ("termination_indirect"
  (lambda (fn object callback done)
    (handler-case
      (unwind-protect (funcall fn object callback) (rplaca done 613))
      (simple-error (c) (values 701 (car done))))))
 ("termination_apply"
  (lambda (fn args done)
    (handler-case
      (unwind-protect (apply fn args) (rplaca done 614))
      (simple-error (c) (values 701 (car done))))))
 ("termination_dynamic"
  (lambda (fn object callback done)
    (handler-case
      (unwind-protect
        (multiple-value-call fn (values object callback))
        (rplaca done 615))
      (simple-error (c) (values 701 (car done))))))
 ("termination_callback"
  (lambda (object) (rplaca object 999)))
 ("termination_operands"
  (lambda (object callback done)
    (handler-case
      (termination_register (progn (rplaca done 21) object)
                            (progn (rplaca done 22) callback))
      (simple-error (c) (car done)))))
 ("termination_nested"
  (lambda (object done)
    (handler-case
      (unwind-protect
        (unwind-protect (termination_register object) (rplaca done 31))
        (rplacd done (car done)))
      (simple-error (c) (values (car done) (cdr done))))))
 ("termination_rethrow"
  (lambda (object done)
    (handler-case
      (handler-bind ((simple-error (lambda (c) (rplaca done 41))))
        (termination_register object))
      (simple-error (c) (car done)))))
 ("termination_noargs"
  (lambda (fn)
    (handler-case (funcall fn)
      (simple-error (c) 701))))
 ("termination_onearg"
  (lambda (fn object)
    (handler-case (funcall fn object)
      (simple-error (c) 701))))
 ("termination_flush" (lambda (done) (rplaca done 11)))
 ("termination_close" (lambda (done) (rplacd done (car done)) (rplaca done 22)))
 ("termination_fd_close_path"
  (lambda (stream flush close done)
   (termination_cancel stream)
   (funcall flush done)
   (funcall close done)
   (values (car done) (cdr done))))
 ("termination_file_cleanup"
  (lambda (stream flush close done)
   (unwind-protect (progn (rplaca done 7) 7)
     (termination_fd_close_path stream flush close done)))))
