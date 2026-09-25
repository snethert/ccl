;;; The host file compiler returns an XFUNCTION, as the other cross targets do.
;;; Its first element is a versioned producer record, never native instructions.
(in-package :wasm32-compiler)

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "FASLENV" "ccl:xdump;faslenv"))

(defvar *wasm32-fasl-contexts* (make-hash-table :test #'eq :weak :key))

(defun wasm32-fasl-pass2 (afunc)
  (unless ccl::*compile-file-truename* (refuse :fasl-file-context))
  (let* ((*module-result-tag* (gensym "WASM32-FASL"))
         (*module-name* (format nil "file_~{~x~}_~d"
                               (map 'list #'char-code
                                    (namestring ccl::*compile-file-pathname*))
                               (incf (gethash ccl::*fasl-compile-time-env*
                                              *wasm32-fasl-contexts* 0))))
         (*bootstrap-front-end* t)
         (*bootstrap-emitted* (make-hash-table :test #'eq))
         (*bootstrap-symbols* nil) (*bootstrap-callees* nil)
         (*bootstrap-dynamic-call* nil) (*bootstrap-self-call* nil)
         (*b-call-mode* t) (*b-callable-metadata* t)
         (*b-integer-service* t) (*b-float-service* t)
         (*b-call-links* nil) (*b-keywords* nil)
         (*wasm32-template-memory* t)
         (module (catch *module-result-tag* (b-call-pass2 afunc)))
         (function (ccl::%alloc-misc 3 target::subtag-xfunction)))
    ;; Child code still needs a whole-file linker in this first producer slice.
    (when (getf module :children) (refuse :fasl-child-code))
    (setf (ccl::%svref function 0)
          (vector :wasm32-fasl-v1 (getf module :name)
                  (getf module :wat) (getf module :pool)
                  (map 'vector (lambda (row) (coerce row 'vector))
                       (getf module :symbols)))
          (ccl::%svref function 1) (ccl::afunc-name afunc)
          (ccl::%svref function 2) 0
          (ccl::afunc-lfun afunc) function)
    afunc))

(in-package :ccl)

(defun wasm32-fasl-dump-function (function)
  (unless (and (typep function 'xfunction) (= (uvsize function) 3))
    (wasm32-compiler::refuse :fasl-function-representation))
  (let* ((record (%svref function 0)))
    (unless (and (simple-vector-p record) (= (length record) 5)
                 (eq (svref record 0) :wasm32-fasl-v1))
      (wasm32-compiler::refuse :fasl-function-version))
    (fasl-out-opcode $fasl-function function)
    (fasl-out-count 1)
    ;; Module text is producer data, consumed before runtime publication.
    ;; Ordinary FASL data ops retain pool object identity and sharing.
    (dolist (index '(1 2))
      (let ((text (svref record index)))
        (unless (and (stringp text) (<= 1 (length text) (ash 1 24))
                     (every (lambda (c) (< (char-code c) 128)) text))
          (wasm32-compiler::refuse :fasl-module-text))
        (fasl-out-count (length text))
        (map nil (lambda (c) (fasl-out-byte (char-code c))) text)))
    (fasl-dump-form (svref record 3))
    (fasl-dump-form (%svref function 1))
    (fasl-dump-form (svref record 4))))
