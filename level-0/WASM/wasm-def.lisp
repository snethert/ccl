;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM32 level-0 overrides live here.

(in-package "CCL")

;; WASM32 uses ARM layout but entrypoints are fixnum table indices.
(defun %fix-fn-entrypoint (func)
  (let* ((codev (uvref func 1)))
    (cond
      ((and (uvectorp codev)
            (> (uvsize codev) 0))
       (setf (uvref func 0) (uvref codev 0)))
      ((fixnump codev)
       (setf (uvref func 0) codev)))
    func))

;; Minimal macptr->fixnum for WASM. The macptr address slot stores the raw
;; pointer (untagged). Convert to a fixnum that represents the byte address.
(defun macptr->fixnum (ptr)
  (declare (optimize (speed 3) (safety 0)))
  (let ((raw (uvref ptr 1)))
    (ash raw 2)))

;;; On native backends this is a LAP function that atomically prepends ptr
;;; to the gcable-pointers kernel global (a linked list through xmacptr.link).
;;; WASM is single-threaded and lacks LAP, so this is a no-op stub for now.
;;; The consequence: gcable macptrs won't have their foreign memory freed
;;; by the GC finalizer.  Acceptable during bootstrap; proper implementation
;;; requires writing to the gcable-pointers kernel global.
(defun set-%gcable-macptrs% (ptr)
  (declare (ignore ptr))
  nil)
