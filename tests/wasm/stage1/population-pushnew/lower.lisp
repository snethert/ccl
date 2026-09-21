(in-package :ccl)
(load (merge-pathnames "base-lower.lisp" *load-pathname*))
(defun lower-population-pushnew (form)
 (labels ((lower (x)
           (cond ((atom x) x) ((eq (car x) 'quote) x)
            ((and (member (car x) '(flet labels)) (some (lambda (d) (member (car d) '(eq eql adjoin))) (second x))) (error "population PUSHNEW local comparison shadow unsupported"))
            ((eq (car x) 'pushnew)
             (unless (and (>= (length x) 3) (consp (third x))
                          (member (car (third x)) '(population-data population-contents))
                          (= (length (third x)) 2)
                          (or (= (length x) 3) (and (= (length x) 5) (eq (fourth x) :test))))
              (error "population PUSHNEW option/place unsupported"))
             ;; CCL binds the item, then the place, then calls ADJOIN and setter.
             (lower (macroexpand-1 (list* 'pushnew (second x)
                                    (list 'population-contents (second (third x))) (cdddr x)))))
            ((eq (car x) 'adjoin)
             (if (= (length x) 3)
              (cons 'pop_adjoin (mapcar #'lower (cdr x)))
              (if (and (= (length x) 5) (eq (fourth x) :test))
               (list 'pop_adjoin_test (lower (second x)) (lower (third x))
                (if (equal (fifth x) '(function eq)) '(function pop_eq) (lower (fifth x))))
               (error "population ADJOIN option unsupported"))))
            (t (mapcar #'lower x)))))
  ;; The established scaffold admission still handles lexical/macro shadows,
  ;; variables, SETF and function references after PUSHNEW is expanded.
  (lower-population-consumer (lower form))))
(setq *population-runtime-entries*
 (append *population-runtime-entries*
 '(("pop_eq" (lambda (a b) (eq a b)))
   ("pop_adjoin" (lambda (item list)
     (let ((rest list) (answer nil))
      (tagbody
       next
        (if rest
         (if (pop_eql item (car rest) nil)
          (progn (setq answer list) (go done))
          (progn (setq rest (cdr rest)) (go next)))
         (setq answer (cons item list)))
       done)
      answer)))
   ("pop_adjoin_test" (lambda (item list test)
     (if test
      (let ((rest list) (answer nil))
       (tagbody
        next
         (if rest
          (if (funcall test item (car rest))
           (progn (setq answer list) (go done))
           (progn (setq rest (cdr rest)) (go next)))
          (setq answer (cons item list)))
        done)
       answer)
      (pop_adjoin item list)))))))
