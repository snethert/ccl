;;; Read-only namespace primitives.  This file follows l0-io on wasm32.
;;; A target buffer is a simple octet vector, never a foreign pointer.
(in-package "CCL")

(defun fd-open (path flags &optional (create-mode #o666))
  (%wasm-file-request 0 path flags create-mode))

(defun fd-read (fd buffer nbytes)
  (%wasm-file-request 1 fd buffer nbytes))

(defun fd-lseek (fd offset whence)
  (%wasm-file-request 2 fd offset whence))

(defun fd-close (fd)
  (%wasm-file-request 3 fd nil nil))

(defun fd-size (fd)
  (%wasm-file-request 4 fd nil nil))

(defun fd-tell (fd)
  (fd-lseek fd 0 1))

(defun %realpath (path)
  (%wasm-file-request 5 path nil nil))

(defun %unix-file-kind (path &optional check-for-link)
  ;; The namespace contains no links; checking for one still evaluates the
  ;; argument, but does not change the kind of an admitted entry.
  (let ((kind (%wasm-file-request 6 path check-for-link nil)))
    (cond ((eq kind 1) :file)
          ((eq kind 2) :directory)
          (t nil))))

(defun fd-write (fd buffer nbytes)
  (%wasm-file-request 7 fd buffer nbytes))
