    (defun core-generic-leaf (ccl::&method context object)
      (declare (ignore context object))
      :leaf)
    (defun core-generic-class-of-function (function)
      (ccl::%wrapper-class (ccl::gf.instance.class-wrapper function)))
    (defun core-generic-function-bits (function)
      (ccl::lfun-bits function))
    (defun core-generic-set-function-bits (function bits)
      (ccl::lfun-bits function bits))
    (defun core-generic-class-of-instance (instance)
      (ccl::%wrapper-class (ccl::instance.class-wrapper instance)))
    (defun core-generic-order (image)
      #+wasm32-target (ccl::compute-dcode #'ccl::eql-specializer-object)
      (progn
        #+wasm32-target (setq ccl::*class-table* (svref image 0)
                             ccl::*eql-specializer-class* (svref image 4))
        (core-collect)
        (loop for method in (ccl::sort-methods (copy-list (svref image 1)) (svref image 3))
              collect (ccl::%method-name method))))
    (defun core-generic-applicable (image)
      #+wasm32-target (ccl::compute-dcode #'ccl::eql-specializer-object)
      (progn
        #+wasm32-target (setq ccl::*class-table* (svref image 0)
                             ccl::*eql-specializer-class* (svref image 4))
        (core-collect)
        (loop for method in (svref image 1)
              when (ccl::%method-applicable-p method (svref image 2) (svref image 3))
              collect (ccl::%method-name method))))

    (defun core-generic-call (image)
      #+wasm32-target (ccl::compute-dcode #'ccl::eql-specializer-object)
      #+wasm32-target
      (setq ccl::*class-table* (svref image 0)
            ccl::*eql-specializer-class* (svref image 4)
            ccl::*standard-class-class* (svref image 5)
            ccl::*clos-initialization-functions* nil)
      (let ((gf (svref image 6)))
        #+wasm32-target (ccl::compute-dcode gf)
        (core-collect)
        (apply gf (svref image 2))))

    (defun core-generic-standard (image)
      (declare (special *generic-trace*))
      #+wasm32-target (ccl::compute-dcode #'ccl::eql-specializer-object)
      #+wasm32-target
      (setq ccl::*class-table* (svref image 0)
            ccl::*eql-specializer-class* (svref image 4)
            ccl::*standard-class-class* (svref image 5)
            ccl::*clos-initialization-functions* nil)
      #+wasm32-target
      (when (> (length image) 7)
        (dolist (gf (svref image 7)) (ccl::compute-dcode gf)))
      (let ((gf (svref image 6)) (*generic-trace* nil))
        #+wasm32-target (ccl::compute-dcode gf)
        (core-collect)
        (let ((result (handler-case
                        (multiple-value-list (catch :dispatch-exit (apply gf (svref image 2))))
                        (simple-error () :simple-error))))
          (values result (reverse *generic-trace*)))))

    (defun core-generic-select (image)
      #+wasm32-target (ccl::compute-dcode #'ccl::eql-specializer-object)
      #+wasm32-target
      (setq ccl::*class-table* (svref image 0)
            ccl::*eql-specializer-class* (svref image 4)
            ccl::*standard-class-class* (svref image 5)
            ccl::*clos-initialization-functions* nil)
      (let ((gf (svref image 6)))
        #+wasm32-target (ccl::compute-dcode gf)
        (core-collect)
        (apply gf (svref image 2))))
    (defun core-generic-updates (image)
      (declare (special *generic-trace*))
      #+wasm32-target
      (progn
        (setq ccl::*class-table* (svref image 0)
              ccl::*eql-specializer-class* (svref image 4)
              ccl::*standard-class-class* (svref image 5)
              ccl::*clos-initialization-functions* nil
              ccl::*initialization-invalidation-alist* nil)
        (dolist (entry (svref image 7)) (set (car entry) (cdr entry)))
        (dolist (gf (svref image 8)) (ccl::compute-dcode gf)))
      (let* ((gf (svref image 6))
             (method (svref image 9))
             (*generic-trace* nil))
        #+wasm32-target (ccl::compute-dcode gf)
        (core-collect)
        (let ((before (apply gf (svref image 2))))
          (add-method gf method)
          (core-collect)
          (let ((during (apply gf (svref image 2)))
                (present (not (null (ccl:memq method (ccl::specializer.direct-methods
                                                   (car (ccl::%method-specializers method))))))))
            (remove-method gf method)
            (core-collect)
            (values before during (apply gf (svref image 2)) present
                    (null (ccl::%method-gf method))
                    (null (ccl:memq method (ccl::specializer.direct-methods
                                         (car (ccl::%method-specializers method))))))))))

    (defun core-generic-prepare (image)
      #+wasm32-target (ccl::compute-dcode #'ccl::eql-specializer-object)
      #+wasm32-target
      (progn
        (setq ccl::*class-table* (svref image 0)
              ccl::*eql-specializer-class* (svref image 4)
              ccl::*standard-class-class* (svref image 5)
              ccl::*clos-initialization-functions* nil
              ccl::*initialization-invalidation-alist* nil)
        (dolist (entry (svref image 7)) (set (car entry) (cdr entry)))
        (dolist (gf (svref image 8)) (ccl::compute-dcode gf))
        (ccl::compute-dcode (svref image 6)))
      image)

    (defun core-generic-failure (image)
      (declare (special *generic-trace*))
      (core-generic-prepare image)
      (let ((gf (svref image 6)) (*generic-trace* nil))
        (core-collect)
        (handler-case
            ;; U1 retains stale code after removing its last method. That
            ;; already-recorded native defect is compared at the protocol.
            #-wasm32-target
            (if (= (svref image 10) 5)
              (apply #'no-applicable-method gf (svref image 2))
              (apply gf (svref image 2)))
            #+wasm32-target (apply gf (svref image 2))
          (ccl::no-applicable-method-exists () :no-applicable-method)
          (program-error () :program-error)
          (simple-error () :simple-error))))

    (defun core-generic-resume (image)
      (declare (special *generic-trace*))
      (core-generic-prepare image)
      (let ((gf (svref image 6)) (method (svref image 9))
            (*generic-trace* nil) (count 0))
        (unwind-protect
            (handler-bind
                ((ccl::no-applicable-method-exists
                   (lambda (condition)
                     (declare (ignore condition))
                     (incf count)
                     (core-collect)
                     (add-method gf method)
                     (invoke-restart 'continue))))
              (let ((result (multiple-value-list (apply gf (svref image 2)))))
                (values result count)))
          (when (ccl::%method-gf method) (remove-method gf method)))))

    (defun core-generic-create (image)
      (declare (special *generic-trace*))
      (core-generic-prepare image)
      (let ((ccl::%all-gfs% (ccl::%cons-population nil))
            (*generic-trace* nil)
            (method (svref image 9)))
        (let ((gf (ccl::%make-gf-instance (class-of (svref image 6))
                    :name 'core-created-generic :lambda-list '(object))))
          (unwind-protect
              (progn
                (add-method gf method)
                (core-collect)
                (values (multiple-value-list (apply gf (svref image 2)))
                        (length (ccl::population.data ccl::%all-gfs%))
                        (eq gf (car (ccl::population.data ccl::%all-gfs%)))
                        (eq gf (ccl::%method-gf method))))
            (when (ccl::%method-gf method) (remove-method gf method))))))

    (defun core-generic-replace (image)
      (declare (special *generic-trace*))
      (core-generic-prepare image)
      (let ((gf (svref image 6)) (old (svref image 9)) (new (svref image 10))
            (*generic-trace* nil))
        (unwind-protect
            (progn
              (add-method gf old)
              (core-collect)
              (let ((before (apply gf (svref image 2))))
                (add-method gf new)
                (core-collect)
                (values before (apply gf (svref image 2))
                        (null (ccl::%method-gf old))
                        (eq gf (ccl::%method-gf new))
                        (length (ccl::%gf-methods gf)))))
          (when (ccl::%method-gf old) (remove-method gf old))
          (when (ccl::%method-gf new) (remove-method gf new)))))

    (defun core-generic-class-of-list (object)
      (svref ccl::*class-table* (if object 2 4)))

    (defun core-generic-arguments (image)
      (declare (special *generic-trace*))
      #+wasm32-target
      (setq ccl::*class-table* (svref image 0)
            ccl::*eql-specializer-class* (svref image 4)
            ccl::*standard-class-class* (svref image 5)
            ccl::*clos-initialization-functions* nil)
      (let ((gf (svref image 6)) (*generic-trace* nil))
        #+wasm32-target (ccl::compute-dcode gf)
        (core-collect)
        (handler-case (multiple-value-list (apply gf (svref image 2)))
          (program-error () :program-error)
          (simple-error () :simple-error))))

    (defun core-generic-builtin (image)
      (core-generic-prepare image)
      #+wasm32-target
      (setq ccl::*cons-class* (svref (svref image 0) 2)
            ccl::*null-class* (svref (svref image 0) 4))
      (core-generic-select image))

    (defun core-generic-empty-cycle (image)
      (declare (special *generic-trace*))
      (core-generic-prepare image)
      (let ((gf (svref image 6)) (method (svref image 9)) (*generic-trace* nil))
        (add-method gf method)
        (let ((present (multiple-value-list (apply gf (svref image 2)))))
          (remove-method gf method)
          (core-collect)
          (values present
            (handler-case
                ;; U1's stale dcode after last removal is an accepted defect.
                #-wasm32-target (apply #'no-applicable-method gf (svref image 2))
                #+wasm32-target (apply gf (svref image 2))
              (ccl::no-applicable-method-exists () :empty))
            (null (ccl::%method-gf method))
            (null (ccl::%gf-methods gf))))))

    (defun core-generic-reader-dispatch (image)
      (core-generic-prepare image)
      (let ((gf #'ccl::eql-specializer-object)
            (method (svref image 9))
            (specializer (car (ccl::%method-specializers (car (svref image 1))))))
        (unwind-protect
            (progn
              (add-method gf method)
              (core-collect)
              (multiple-value-list (ccl::eql-specializer-object specializer)))
          (when (ccl::%method-gf method) (remove-method gf method)))))
