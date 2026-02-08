;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM helper entrypoint for producing doc/wasm/root.image from inside
;;; the wasm runtime without relying on the interactive toplevel loop.

(in-package "CCL")

(defparameter *wasm-make-real-image-entry-marker* "WASM-MAKE-REAL-IMAGE-ENTRY-V1")

(defun wasm-make-real-image-entry ()
  (declare (ignorable *wasm-make-real-image-entry-marker*))
  (unless (fboundp 'open-dumplisp-file)
    (ignore-errors (require "DUMPLISP")))
  (unless (and (fboundp 'open-dumplisp-file)
               (fboundp '%save-application))
    (error "dumplisp helpers are unavailable; ensure DUMPLISP is loadable."))
  (set '%toplevel-function% #'toplevel-loop)
  (let* ((fd (open-dumplisp-file "doc/wasm/root.image")))
    (unless (and fd (integerp fd) (>= fd 0))
      (error "open-dumplisp-file failed for doc/wasm/root.image: ~s" fd))
    (unwind-protect
      (%save-application fd 0)
      (ignore-errors (fd-close fd))))
  (%set-toplevel nil)
  nil)
