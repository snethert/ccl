(in-package "CCL")

(defun loader-keywords (x &key (amount 7 amount-p)
                             ((ccl::offset offset) 2 offset-p)
                             &allow-other-keys)
  (values (cons x (cons amount offset)) amount-p offset-p))

(defun loader-nested-keywords (x)
  (let ((function (lambda (&key (amount 4)) (cons x amount))))
    (funcall function :amount 9)))

(defun loader-apply-keywords (x)
  (apply #'loader-keywords (list x :amount 5)))
