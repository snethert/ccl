;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 vinsn templates (stub).

(in-package "CCL")

(defvar *wasm-vinsn-templates* (make-hash-table :test #'eq))

(defun %define-wasm-vinsn (backend vinsn-name results args temps body)
  (declare (ignore backend vinsn-name results args temps body))
  (error "WASM vinsn templates are not implemented yet."))

(provide "WASM-VINSNS")
