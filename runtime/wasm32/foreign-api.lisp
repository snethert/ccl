;;; Lisp-facing foreign Wasm API. The embedding owns declarations and imports.
(in-package "CCL")

(defun %wasm-foreign-request (operation payload)
  (let ((status (%wasm-host-process-request 15 operation payload)))
    (when (minusp status)
      (error "Foreign Wasm operation ~D failed (~D)." operation status))
    status))

(defun open-wasm-library (name)
  "Open an embedding-declared named library on the current Worker."
  (%wasm-foreign-request 0 name))

(defun close-wasm-library (library)
  (%wasm-foreign-request 1 library)
  nil)

(defun wasm-call (library name &rest arguments)
  "Call a declared export. Pointer arguments are WASM-BUFFER-RANGE tokens."
  (let ((request (vector library name (coerce arguments 'vector) nil)))
    (%wasm-foreign-request 2 request)
    (values-list (coerce (svref request 3) 'list))))

(defun allocate-wasm-buffer (library size)
  (%wasm-foreign-request 3 (vector library size)))

(defun release-wasm-buffer (handle)
  (not (zerop (%wasm-foreign-request 4 handle))))

(defun wasm-buffer-range (handle &optional (offset 0))
  (%wasm-foreign-request 5 (vector handle offset)))

(defun write-wasm-buffer (handle bytes &optional (offset 0))
  (%wasm-foreign-request 6 (vector handle offset bytes))
  bytes)

(defun read-wasm-buffer (handle size &optional (offset 0))
  (let ((bytes (make-array size :element-type '(unsigned-byte 8))))
    (%wasm-foreign-request 7 (vector handle offset bytes))
    bytes))

(defmacro with-wasm-buffer ((handle library size) &body body)
  "Release once on every exit, preserving a primary error or nonlocal exit."
  (let ((completed (gensym "COMPLETED")))
    `(let ((,handle (allocate-wasm-buffer ,library ,size)) (,completed nil))
       (unwind-protect
            (multiple-value-prog1 (progn ,@body) (setq ,completed t))
         (if ,completed
           (release-wasm-buffer ,handle)
           (ignore-errors (release-wasm-buffer ,handle)))))))

(defun finalize-wasm-buffer (handle lifetime)
  "Queue HANDLE for release when heap object LIFETIME becomes unreachable.
Keep LIFETIME reachable until the buffer's last use. Registration is once only."
  (%wasm-foreign-request 8 (vector handle lifetime))
  handle)

(defun drain-wasm-finalizers ()
  "Run one batch of queued releases on this Worker, outside collection."
  (%wasm-foreign-request 9 nil))

(defun write-wasm-string (handle string &key encoding (offset 0))
  "Copy a simple string as explicit UTF-8. Return the byte count; add no NUL."
  (unless (eq encoding :utf-8)
    (error "Foreign string encoding must be :UTF-8."))
  (%wasm-foreign-request 10 (vector handle offset string 0)))

(defun read-wasm-string (handle size &key encoding (offset 0))
  "Decode exactly SIZE UTF-8 bytes, refusing malformed sequences."
  (unless (eq encoding :utf-8)
    (error "Foreign string encoding must be :UTF-8."))
  (let ((request (vector handle offset size 0 nil)))
    (%wasm-foreign-request 11 request)
    (svref request 4)))
