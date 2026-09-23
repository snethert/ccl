(in-package :wasm32-compiler)

;;; Compile the complete file environment. Only CLASS-TYPEP joins this
;;; execution unit: internal macro expander names are not replacement CL
;;; function definitions, and do not displace the numeric oracle entries.
(let ((candidates *core-candidates*) (modules *core-modules*)
      (native (loop for name being the hash-keys of *core-native-functions*
                    using (hash-value function) collect (cons name function))))
  (core-compile-file "ccl:level-1;l1-typesys.lisp" t)
  (core-compile-file "ccl:level-1;l1-typesys.lisp")
  (let ((entry (find 'ccl::class-typep *core-candidates*
                     :key (lambda (row) (second (first row))))))
    (assert entry)
    (setq *core-candidates* (cons entry candidates)
          *core-modules* (cons (second entry) modules)))
  (dolist (entry native)
    (unless (eq (car entry) 'ccl::class-typep)
      (setf (gethash (car entry) *core-native-functions*) (cdr entry)))))
