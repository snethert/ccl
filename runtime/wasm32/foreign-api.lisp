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
