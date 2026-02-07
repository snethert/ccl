;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 external-call (FFI) support (minimal, i32-only).

(in-package "CCL")

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "NXENV")
  (require "WASM-ARCH"))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (unless (assq '%wasm-ff-call *next-nx-operators*)
    (push '(%wasm-ff-call 0 :infer) *next-nx-operators*))
  (unless (assq 'wasm-ff-call *next-nx-operators*)
    (push '(wasm-ff-call 0 :infer) *next-nx-operators*))
  (next-nx-defops))

(defparameter *wasm-ffi-supported-repr-types*
  '(:address
    :signed-fullword :unsigned-fullword
    :signed-halfword :unsigned-halfword
    :signed-byte :unsigned-byte
    :void))

(defun wasm-ffi-supported-repr-p (spec)
  (member spec *wasm-ffi-supported-repr-types* :test #'eq))

(defun wasm-ffi-extract-entry-name (entry)
  (cond
    ((stringp entry) entry)
    ((symbolp entry) (symbol-name entry))
    ((and (consp entry)
          (eq (car entry) '%reference-external-entry-point)
          (consp (cdr entry)))
     (let ((inner (cadr entry)))
       (when (and (consp inner)
                  (eq (car inner) 'load-time-value)
                  (consp (cdr inner)))
         (let ((ext (cadr inner)))
           (when (and (consp ext)
                      (eq (car ext) 'external)
                      (consp (cdr ext)))
             (let ((name (cadr ext)))
               (cond
                 ((stringp name) name)
                 ((symbolp name) (symbol-name name))
                 (t nil))))))))
    (t nil)))

(defnx1 nx1-wasm-ff-call ((%wasm-ff-call)) context (name &rest arg-specs-and-result-spec)
  (declare (ignorable context))
  (unless (stringp name)
    (error "WASM FFI requires a literal external name string, got ~s" name))
  (let* ((specs nil)
         (vals nil)
         (arg-specs (butlast arg-specs-and-result-spec))
         (result-spec (car (last arg-specs-and-result-spec))))
    (unless (evenp (length arg-specs))
      (error "odd number of arg-specs"))
    (loop
      (when (null arg-specs) (return))
      (let* ((arg-keyword (pop arg-specs))
             (value (pop arg-specs)))
        (unless (wasm-ffi-supported-repr-p arg-keyword)
          (error "Unsupported WASM FFI argument type: ~s" arg-keyword))
        (push arg-keyword specs)
        (push value vals)))
    (unless (or (eq result-spec :void)
                (wasm-ffi-supported-repr-p result-spec))
      (error "Unsupported WASM FFI result type: ~s" result-spec))
    (when (eq result-spec :address)
      (error "WASM FFI does not support :address results"))
    (make-acode (%nx1-operator typed-form)
                (case result-spec
                  (:double-float 'double-float)
                  (:single-float 'single-float)
                  (:address 'macptr)
                  (:signed-doubleword '(signed-byte 64))
                  (:unsigned-doubleword '(unsigned-byte 64))
                  (:signed-fullword '(signed-byte 32))
                  (:unsigned-fullword '(unsigned-byte 32))
                  (:signed-halfword '(signed-byte 16))
                  (:unsigned-halfword '(unsigned-byte 16))
                  (:signed-byte '(signed-byte 8))
                  (:unsigned-byte '(unsigned-byte 8))
                  (t t))
                (make-acode (%nx1-operator wasm-ff-call)
                            name
                            (nreverse specs)
                            (mapcar (lambda (val) (nx1-form :value val)) (nreverse vals))
                            result-spec
                            nil)
                nil)))

(defun setup-wasm-ftd (backend)
  (or (backend-target-foreign-type-data backend)
      (let ((ftd
             (make-ftd :interface-db-directory nil
                       :interface-package-name "WASM"
                       :attributes '(:bits-per-word 32
                                     :bits-per-long 32
                                     :signed-char nil
                                     :struct-by-value nil)
                       :ff-call-expand-function
                       (intern "EXPAND-FF-CALL" "WASM")
                       :ff-call-struct-return-by-implicit-arg-function
                       (intern "RECORD-TYPE-RETURNS-STRUCTURE-AS-FIRST-ARG" "WASM")
                       :callback-bindings-function
                       (intern "GENERATE-CALLBACK-BINDINGS" "WASM")
                       :callback-return-value-function
                       (intern "GENERATE-CALLBACK-RETURN-VALUE" "WASM"))))
        (install-standard-foreign-types ftd)
        (let ((*target-ftd* ftd))
          ;; Minimal struct types needed by l1 runtime utilities.
          (unless (%find-foreign-record :timeval)
            (def-foreign-type :timeval
              (:struct :timeval
               (:tv_sec :signed-long)
               (:tv_usec :signed-fullword))))
          (unless (%find-foreign-record :timespec)
            (def-foreign-type :timespec
              (:struct :timespec
               (:tv_sec :signed-long)
               (:tv_nsec :signed-fullword))))
          (unless (%find-foreign-record :stat)
            (def-foreign-type :stat
              (:struct :stat
               (:st_mode :unsigned-long)
               (:st_size :signed-long)
               (:st_mtime :signed-long)
               (:st_mtim (:struct :timespec))
               (:st_mtimespec (:struct :timespec))
               (:st_ino :unsigned-long)
               (:st_uid :unsigned-long)
               (:st_blksize :signed-long)
               (:st_mtime_nsec :signed-long)
               (:st_gid :unsigned-long)
               (:st_dev :unsigned-long)
               (:st_flags :unsigned-long))))
          (unless (%find-foreign-record :passwd)
            (def-foreign-type :passwd
              (:struct :passwd
               (:pw_name :address)
               (:pw_uid :unsigned-long)
               (:pw_dir :address))))
        (setf (backend-target-foreign-type-data backend) ftd)))))

(in-package "WASM")

(defun record-type-returns-structure-as-first-arg (_rtype)
  (declare (ignore _rtype))
  nil)

(defun generate-callback-bindings (&rest _args)
  (declare (ignore _args))
  (error "WASM FFI callbacks are not supported"))

(defun generate-callback-return-value (&rest _args)
  (declare (ignore _args))
  (error "WASM FFI callbacks are not supported"))

(defun expand-ff-call (callform args &key (arg-coerce #'ccl::null-coerce-foreign-arg)
                                     (result-coerce #'ccl::null-coerce-foreign-result))
  (declare (ignore result-coerce))
  (let* ((name (ccl::wasm-ffi-extract-entry-name (cadr callform))))
    (unless name
      (error "WASM FFI requires a literal external name; got ~s" callform))
    (let* ((result-type-spec (or (car (last args)) :void))
           (args (butlast args)))
      (unless (evenp (length args))
        (error "~s should be an even-length list of alternating foreign types and values" args))
      (ccl::collect ((argforms))
        (do* ((args args (cddr args)))
             ((null args))
          (let* ((arg-type-spec (car args))
                 (arg-value-form (cadr args))
                 (ftype (ccl::parse-foreign-type arg-type-spec))
                 (rtype (ccl::foreign-type-to-representation-type ftype)))
            (unless (ccl::wasm-ffi-supported-repr-p rtype)
              (error "Unsupported WASM FFI argument type: ~s" arg-type-spec))
            (argforms rtype)
            (argforms (funcall arg-coerce arg-type-spec arg-value-form))))
        (let ((result-repr
               (if (eq result-type-spec :void)
                 :void
                 (let* ((rtype (ccl::parse-foreign-type result-type-spec)))
                   (ccl::foreign-type-to-representation-type rtype)))))
          (unless (ccl::wasm-ffi-supported-repr-p result-repr)
            (error "Unsupported WASM FFI result type: ~s" result-type-spec))
          (when (eq result-repr :address)
            (error "WASM FFI does not support :address results"))
          `(ccl::%wasm-ff-call ,name ,@(argforms) ,result-repr))))))

(provide "WASM-FFI")
