(in-package :wasm32-compiler)

(defmacro validation-increment (form)
  `(1+ ,form))

(define-symbol-macro validation-offset 3)

(defun validation-helper (x)
  (+ x validation-offset))

(defun validation-file-environment (x)
  (validation-increment (validation-helper x)))

(defun validation-condition (numerator)
  (handler-case (truncate numerator 0)
    (division-by-zero (condition)
      (declare (ignore condition))
      (core-collect)
      (list numerator t))))

(declaim (special *validation-counter*))

(defun validation-global (x)
  (incf *validation-counter* x)
  (core-collect)
  *validation-counter*)
