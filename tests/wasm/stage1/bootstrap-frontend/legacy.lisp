(in-package :wasm32-compiler)
(defun frontend-legacy (out)
  (loop for source in '("(lambda () nil)" "(lambda () (values 1 2))"
                        "(lambda (x) (car x))" "(lambda (x) (eq x (cdr x)))"
                        "(lambda (x) (unwind-protect (values x (car x)) (rplacd x nil)))"
                        "(lambda (x) (catch x (throw x (values 1 2))))"
                        "(lambda (x) (let ((y x)) (lambda () (setq y (cdr y)))))"
                        "(lambda (x) (flet ((f (y) (car y))) (f x)))")
        for i from 0 do
    (let* ((name (format nil "legacy_~d" i))
           (result (compile-call-module source name nil)))
      (dolist (m (cons result (getf result :children)))
        (with-open-file (s (concatenate 'string out (getf m :name) ".legacy")
                           :direction :output :if-exists :error)
          (write-string (getf m :wat) s))))))
