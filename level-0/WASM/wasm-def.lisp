;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 level-0 overrides live here.

(in-package "CCL")

;; WASM32 uses ARM layout but entrypoints are fixnum table indices.
(defun %fix-fn-entrypoint (func)
  (let* ((codev (uvref func 1))
         (entry (uvref codev 0)))
    (setf (uvref func 0) entry)
    func))

;; Minimal macptr->fixnum for WASM. The macptr address slot stores the raw
;; pointer (untagged). Convert to a fixnum that represents the byte address.
(defun macptr->fixnum (ptr)
  (declare (optimize (speed 3) (safety 0)))
  (let ((raw (uvref ptr 1)))
    (ash raw 2)))
