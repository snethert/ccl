(in-package :ccl)

;; Use the native image's arch macros, without copying their implementation.
(let* ((immediate (arch::arch-macro-function :x8664 'immediate-p-macro))
       (identity (arch::arch-macro-function :x8664 'hashed-by-identity)))
  (assert (and immediate identity))
  (let* ((function
          (compile nil
                   `(lambda (x)
                      (values ,(funcall immediate '(immediate-p-macro x) nil)
                              ,(funcall identity '(hashed-by-identity x) nil)))))
         (values (multiple-value-list (funcall function 1.5s0))))
    (assert (equal values '(t t)))
    (format t "AUDIT158-SINGLE-IDENTITY ~s~%" values)))
(quit)
