;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 vinsn templates (stub).

(in-package "CCL")

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "VINSN"))

(defvar *wasm-vinsn-templates* (make-hash-table :test #'eq))

(defun %define-wasm-vinsn (backend vinsn-name results args temps body)
  (let* ((attrs 0))
    (when (consp vinsn-name)
      (setf attrs (encode-vinsn-attributes (cdr vinsn-name))
            vinsn-name (car vinsn-name)))
    (unless (and (symbolp vinsn-name) (eq *CCL-PACKAGE* (symbol-package vinsn-name)))
      (setf vinsn-name (intern (string vinsn-name) *CCL-PACKAGE*)))
    (let* ((template (make-vinsn-template :name vinsn-name
                                          :result-vreg-specs results
                                          :argument-vreg-specs args
                                          :temp-vreg-specs temps
                                          :body body
                                          :attributes attrs)))
      (set-vinsn-template vinsn-name template (backend-p2-vinsn-templates backend))
      vinsn-name)))

(defmacro define-wasm-vinsn (vinsn-name (results args &optional temps) &body body)
  `(%define-vinsn *wasm-backend* ,vinsn-name ,results ,args ,temps ,body))

(provide "WASM-VINSNS")
