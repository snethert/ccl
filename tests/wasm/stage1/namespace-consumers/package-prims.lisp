(in-package :ccl)

;;; The linker resolves package literals by name in its admitted package set.
;;; No native package object or native address enters a target constant pool.
(defvar *wasm-package-literals* nil)

(defun %wasm-package-literal (name)
  (or (cdr (assoc (string name) *wasm-package-literals* :test #'string=))
      (error "Package is absent from the linked symbol set: ~s" name)))

(defun %wasm-intern (name &optional (package *package*))
  (check-type name string)
  (unless (packagep package)
    (setq package (%wasm-package-literal (string package))))
  (%wasm-symbol-intern (ensure-simple-string name) package nil))

(defun %wasm-find-symbol (name &optional (package *package*))
  (check-type name string)
  (unless (packagep package)
    (setq package (%wasm-package-literal (string package))))
  (%wasm-symbol-find (ensure-simple-string name) package nil))
