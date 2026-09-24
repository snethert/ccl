(in-package "CCL")

(defun namespace-read-close (path buffer)
  (let ((fd (fd-open path 0)))
    (unwind-protect
        (values (fd-read fd buffer 3) (fd-tell fd) (fd-size fd))
      (fd-close fd))))

(defun namespace-unwind-close (path)
  (let ((fd (fd-open path 0)))
    (catch 'namespace-done
      (unwind-protect
          (throw 'namespace-done fd)
        (fd-close fd)))))

(defun namespace-open-effects (path cell)
  (fd-open path (progn (setf (car cell) 1) 0)
           (progn (setf (cdr cell) (car cell)) #o666)))
