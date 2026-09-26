(in-package "CCL")

;;; A separate FASL must recover the defining file's canonical binding name.
(defun loader-level1-setter-second ()
  '#.(setf-function-name 'loader-level1-cell))
