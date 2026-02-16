;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 I/O functions.

(in-package "CCL")

;;; Return the negated errno value as a fixnum and clear it.
;;; On ARM, this reads tcr.errno-loc via LAP. On WASM, errno is
;;; maintained by the microkernel in the TCR struct.
;;; For bootstrap, return 0 — proper implementation requires
;;; verified TCR field offsets for WASM32.
(defun %get-errno ()
  0)
