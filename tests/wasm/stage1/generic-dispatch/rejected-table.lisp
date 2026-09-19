  ("gd_table" (lambda (state &rest args)
   (labels ((select (methods)
              (if methods
                (if (if (eq (car (car methods)) t) t (eq (car (car methods)) (car args)))
                  (apply (cdr (car methods)) state args)
                  (select (cdr methods)))
                (apply #'gd_missing state args))))
     (select (car state)))))
