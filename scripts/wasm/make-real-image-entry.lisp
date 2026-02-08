;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM helper entrypoint for producing doc/wasm/root.image from inside
;;; the wasm runtime without relying on the interactive toplevel loop.

(in-package "CCL")

(defparameter *wasm-make-real-image-entry-marker* "WASM-MAKE-REAL-IMAGE-ENTRY-V1")
(declaim (special %wasm-compiled-modules% %wasm-const-pools%))

(defun wasm-make-real-image-entry ()
  (declare (ignorable *wasm-make-real-image-entry-marker*))
  :wasm-real-image-ready)
