;;; -*- Mode: Lisp; Package: CCL -*-
(in-package :ccl)

;;; The owner supplies callable capabilities. Absence is an error, never a
;;; successful no-op. This first cut does not replace linux-files in startup.
(defvar *wasm-host-services* nil)

(defun wasm-host-service (name)
  (or (cdr (assq name *wasm-host-services*))
      (error "Host service ~s is unavailable" name)))

(defun getenv (key)
  (funcall (wasm-host-service :getenv) (require-type key 'string)))

(defun get-universal-time ()
  (require-type (funcall (wasm-host-service :universal-time)) '(integer 0 *)))

(defun cpu-count ()
  (declare (special *cpu-count*))
  (or *cpu-count*
      (setq *cpu-count*
            (require-type (funcall (wasm-host-service :cpu-count)) '(integer 1 *)))))

(defun signal-semaphore (semaphore)
  (funcall (wasm-host-service :signal-semaphore) semaphore))

(defun wait-on-semaphore (semaphore &optional flag (whostate "semaphore wait"))
  (funcall (wasm-host-service :wait-on-semaphore) semaphore flag whostate)
  t)

(defun timed-wait-on-semaphore (semaphore duration &optional notification)
  (funcall (wasm-host-service :timed-wait-on-semaphore) semaphore duration notification))

(defun yield ()
  (funcall (wasm-host-service :yield)))
