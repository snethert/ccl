;; The checkout's numeric work closes these existing l0-utils definitions.
;; Supply boundary inputs instead of suppressing the oracle's coverage check.
(let ((prior (symbol-function 'wasm32-compiler::core-inputs)))
  (setf (symbol-function 'wasm32-compiler::core-inputs)
        (lambda (name)
          (case name
            (ccl::s32->u32
             (values '((-2147483648) (-536870913) (-536870912) (-1)
                       (0) (1) (536870911) (536870912) (2147483647)) t))
            (ccl::u32->s32
             (values '((0) (1) (536870911) (536870912) (2147483647)
                       (2147483648) (4294967295)) t))
            (t (funcall prior name))))))
