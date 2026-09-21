;;; -*- Mode: Lisp; Package: CCL; -*-
;;; Wasm entry points for primitives open-coded by its pass 2.
;;; Like the native LAP entries, these remain callable through function cells.
(in-package "CCL")

(defun lisptag (object)
  (lisptag object))

(defun fulltag (object)
  (fulltag object))

(defun typecode (object)
  (typecode object))

(defun %slot-ref (instance index)
  (%slot-ref instance index))
