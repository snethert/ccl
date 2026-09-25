    ;; Independent diagnostic copies, never published as production functions.
    (call-with-target
     (lambda ()
       (let ((*package* (find-package "CCL")))
         (with-open-file (input (concatenate 'string out "array-boundary.lisp"))
           (loop for form = (read input nil :end) until (eq form :end) do
             (when (and (consp form) (eq (car form) 'defun))
               (dolist (row '((ccl::%wasm-array-subscript ccl::loader-array-mutant-lower
                              (>= ccl::index 0))
                             (ccl::%wasm-array-subscript ccl::loader-array-mutant-upper
                              (< ccl::index ccl::dimension))
                             (ccl::%wasm-array-index ccl::loader-array-mutant-header
                              "(= (the fixnum (typecode array)) target::subtag-arrayH)")
                             (ccl::%wasm-array-index ccl::loader-array-mutant-rank
                              "(= (the fixnum (ccl::%svref array target::arrayH.rank-cell)) ccl::rank)")))
                 (when (eq (second form) (first row))
                   (let* ((clause (if (stringp (third row)) (read-from-string (third row)) (third row)))
                          (copy (subst t clause (copy-tree form) :test #'equal)))
                     (assert (not (equal copy form)))
                     (setf (second copy) (second row))
                     (write copy :stream s) (terpri s))))))))))
