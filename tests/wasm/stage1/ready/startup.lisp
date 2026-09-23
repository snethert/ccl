(in-package :wasm32-compiler)

;;; The selected image already contains initialized classes and method bodies.
;;; Reset host-lifetime state, publish its roots, and select uncached dispatch.
(defun ready-initialize (image)
  (core-condition-prepare image)
  (let ((gfs (cons (symbol-function 'ccl::eql-specializer-object) (svref image 8))))
    (dolist (entry (first (svref image 12)))
      (pushnew (car entry) gfs :test #'eq))
    (setq ccl::%all-gfs% (ccl::%cons-population gfs)
          ccl::*enable-automatic-termination* nil
          ccl::*%periodic-tasks%* nil))
  (values (length (ccl::population.data ccl::%all-gfs%))
          ccl::*enable-automatic-termination*
          ccl::*%periodic-tasks%*))

(defun ready-check (image)
  (let ((count 0))
    (dolist (entry (svref image 11))
      (unless (eq (find-class (car entry)) (cdr entry))
        (error "The class image lost a class cell."))
      (incf count))
    (let ((gfs (ccl::population.data ccl::%all-gfs%)))
      (dolist (gf (cons (symbol-function 'ccl::eql-specializer-object) (svref image 8)))
        (unless (ccl::memq gf gfs) (error "A projected generic function was lost.")))
      (dolist (entry (first (svref image 12)))
        (unless (ccl::memq (car entry) gfs) (error "An invalidation generic function was lost."))))
    (unless (and (not ccl::*enable-automatic-termination*)
                 (not ccl::*%periodic-tasks%*))
      (error "The image startup roots are not initialized."))
    (core-collect)
    (let ((condition (make-condition 'cpl-derived)))
      (values count
              (length (ccl::population.data ccl::%all-gfs%))
              (slot-value condition 'payload)
              (slot-value condition 'other)
              (handler-case (error "READY condition dispatch")
                (simple-error () :caught))))))

(defun ready-start (image)
  (ready-initialize image)
  (core-collect)
  (ready-check image))
