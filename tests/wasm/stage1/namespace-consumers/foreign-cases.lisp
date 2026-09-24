(in-package :wasm32-compiler)

(defvar *namespace-database-attempts* 0)

(defun namespace-database-denied (&rest arguments)
  (declare (ignore arguments))
  (incf *namespace-database-attempts*)
  (error "Namespace initialization attempted to open an interface database."))

(defun namespace-foreign-check ()
  (let ((saved (fboundp 'ccl::cdb-open)))
    (unwind-protect
        (progn
          (ccl::%fhave 'ccl::cdb-open #'namespace-database-denied)
          (setq *namespace-database-attempts* 0)
          (namespace-foreign-initialize)
          (namespace-foreign-cases))
      (if saved
        (ccl::%fhave 'ccl::cdb-open saved)
        (fmakunbound 'ccl::cdb-open)))))

(defun namespace-foreign-cases ()
  (let ((ftd ccl::*host-ftd*))
    (list (null (ccl::ftd-interface-db-directory ftd))
          (getf (ccl::ftd-attributes ftd) :bits-per-word)
          (mapcar (lambda (name)
                    (let ((type (ccl::parse-foreign-type name ftd)))
                      (list name (ccl::foreign-type-bits type)
                            (ccl::foreign-type-alignment type))))
                  '(:signed-char :short :int :long :address :float :double))
          (eq (ccl::parse-foreign-type :int ftd)
              (ccl::parse-foreign-type :signed-int ftd))
          (ccl::foreign-type-bits (ccl::parse-foreign-type '(:* :int) ftd))
          (ccl::foreign-type-bits (ccl::parse-foreign-type '(:array :int 3) ftd))
          *namespace-database-attempts*)))
