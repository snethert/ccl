(in-package :wasm32-compiler)

(defun validation-probe-cases ()
  (let ((image (cpl-image 'cpl-left)))
    (setf (svref (svref image 0) wasm32::subtag-istruct) (find-class 'hash-table))
    ;; The CHECK entry observes startup, without invoking the initializer.
    ;; Native execution follows the explicit entry order below.
    (loop for name in '(ready-initialize ready-check ready-start)
          collect (list name (list (list image))))))
