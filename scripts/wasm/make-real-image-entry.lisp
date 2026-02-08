;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM helper entrypoint for producing doc/wasm/root.image from inside
;;; the wasm runtime without relying on the interactive toplevel loop.

(in-package "CCL")

(defparameter *wasm-make-real-image-entry-marker* "WASM-MAKE-REAL-IMAGE-ENTRY-V1")
(declaim (special %wasm-compiled-modules% %wasm-const-pools%))

(defparameter *wasm-real-image-fasls*
  '("level-1.lafsl"
    "bin/lists.lafsl"
    "bin/sequences.lafsl"
    "bin/hash.lafsl"
    "bin/defstruct.lafsl"
    "bin/dll-node.lafsl"
    "bin/chars.lafsl"
    "bin/dumplisp.lafsl")
  "Core fasls required for a usable root.image in wasm runtime mode.")

(defun wasm-make-real-image-entry ()
  (declare (ignorable *wasm-make-real-image-entry-marker*))
  (dolist (fasl *wasm-real-image-fasls*)
    (%fasload fasl))
  :wasm-real-image-ready)
