(in-package :wasm32-compiler)

;;; Extend the projected protocol with CCL's own method bodies. The existing
;;; method reader finds each unqualified DEFMETHOD by name and specializers,
;;; and PARSE-DEFMETHOD supplies the native calling convention.
(setq *condition-method-specs*
      (append *condition-method-specs*
        '((ccl::slot-value-using-class (ccl::funcallable-standard-class t ccl::standard-effective-slot-definition)
            core-condition-gf-slot-value)
          ((setf ccl::slot-value-using-class) (t ccl::funcallable-standard-class t ccl::standard-effective-slot-definition)
            core-condition-gf-set-slot-value)
          (ccl::slot-boundp-using-class (ccl::funcallable-standard-class t ccl::standard-effective-slot-definition)
            core-condition-gf-slot-boundp)
          (no-applicable-method (t) core-condition-no-applicable-method)
          (ccl::add-dependent (ccl::class t) core-condition-add-class-dependent)
          (ccl::add-dependent (standard-generic-function t) core-condition-add-gf-dependent)
          (ccl::remove-dependent (ccl::class t) core-condition-remove-class-dependent)
          (ccl::remove-dependent (standard-generic-function t) core-condition-remove-gf-dependent)
          (ccl::map-dependents (ccl::class t) core-condition-map-class-dependents)
          (ccl::map-dependents (standard-generic-function t) core-condition-map-gf-dependents)
          (ccl::generic-function-lambda-list (standard-generic-function) core-condition-gf-lambda-list)
          (ccl::compute-class-precedence-list (ccl::class) core-condition-compute-cpl)
          (ccl::compute-default-initargs (ccl::slots-class) core-condition-default-initargs)
          (slot-missing (t t t t) core-condition-slot-missing)
          (slot-unbound (t t t) core-condition-slot-unbound)
          (close (stream) core-condition-stream-close)
          (close (ccl::basic-stream) core-condition-basic-close (:after))
          (close (ccl::basic-output-stream) core-condition-output-close (:before))
          (open-stream-p (ccl::basic-stream) core-condition-stream-open)
          (ccl::stream-force-output (ccl::string-output-stream) core-condition-string-force)
          ((setf ccl::stream-ioblock) (t ccl::basic-stream) core-condition-stream-set-block))))

;;; CCL synthesizes these readers from the native class slot declarations.
;;; The image builder joins them to the actual methods and slot definitions.
(setq *condition-reader-specs*
      (append *condition-reader-specs*
        '((ccl::slot-definition-location ccl::effective-slot-definition ccl::location)
          (class-name ccl::class ccl::name)
          (ccl::class-own-wrapper ccl::class ccl::own-wrapper)
          (ccl::class-direct-superclasses ccl::class ccl::direct-superclasses)
          (ccl::class-direct-subclasses ccl::class ccl::direct-subclasses)
          (ccl::slot-definition-allocation ccl::slot-definition ccl::allocation)
          (ccl::generic-function-name ccl::funcallable-standard-object ccl::name)
          (ccl::generic-function-methods generic-function ccl::methods))))

(dolist (spec *condition-reader-specs*)
  (destructuring-bind (name class slot) spec
    (let* ((class (find-class class))
           (slotd (find slot (ccl:class-slots class) :key #'ccl:slot-definition-name)))
      (assert slotd)
      (assert (find-method (fdefinition name) nil (list class))))))
