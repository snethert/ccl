(in-package :ccl)

;; Observe the existing initializer with a fresh descriptor of the registered
;; wasm32 shape. This is a native prerequisite check, not target boot execution.
(let* ((*warn-if-redefine-kernel* nil)
       (saved (fdefinition 'cdb-open))
       (attempts 0)
       (ftd (make-ftd :interface-package-name "WASM32-OS"
                      :attributes '(:bits-per-word 32)
                      :ff-call-expand-function
                      (lambda (&rest args)
                        (declare (ignore args))
                        (error "Native FFI excluded")))))
  (unless (find-package "WASM32-OS")
    (make-package "WASM32-OS" :use nil))
  (unwind-protect
       (progn
         (setf (fdefinition 'cdb-open)
               (lambda (&rest args)
                 (declare (ignore args))
                 (incf attempts)
                 (error "Unexpected interface database access")))
         (install-standard-foreign-types ftd)
         (let* ((types '(:signed-char :short :int :long :address :float :double))
                (sizes (mapcar (lambda (name)
                                 (foreign-type-bits (parse-foreign-type name ftd)))
                               types)))
           (assert (equal sizes '(8 16 32 32 32 32 64)))
           (assert (zerop attempts))
           (assert (null (ftd-interface-db-directory ftd)))
           (with-open-file (stream (getenv "NAMESPACE_FTD_RESULTS")
                                   :direction :output :if-exists :supersede)
             (format stream "{~s:~s,~s:~d,~s:[~{~d~^,~}],~s:false}~%"
                     "status" "PASS" "database_attempts" attempts
                     "type_bits" sizes "target_execution"))))
    (setf (fdefinition 'cdb-open) saved)))
