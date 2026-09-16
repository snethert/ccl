;;; Extend the existing native corpus; no shared source or saved image changes.
(in-package :census-finite-probes)
(defvar *escaped* nil)
(setf *probes*
 (append *probes*
 '(("captured-constant" finite ("COMMON-LISP::1+")
    (lambda (x) (let* ((callee #'1+) (thunk (lambda (v) (funcall callee v))))
                  (funcall thunk x))) ((5)) (6))
   ("escaping-capture" finite ("COMMON-LISP::1+")
    (lambda (x) (let ((callee #'1+)) (setq *escaped* (lambda (v) (funcall callee v)))
                  (funcall *escaped* x))) ((5)) (6))
   ("captured-write-new" unresolved nil
    (lambda (other x) (let ((callee #'1+))
      (setq *escaped* (lambda (v) (funcall callee v)))
      (setq callee other) (funcall *escaped* x))) ((1- 5)) (4))
   ("captured-external-parameter" unresolved nil
    (lambda (callee x) (setq *escaped* (lambda (v) (funcall callee v)))
                       (funcall *escaped* x)) ((1- 5)) (4))
   ("local-parameter" finite ("COMMON-LISP::1+")
    (lambda (x) (flet ((invoke (callee v) (funcall callee v))) (invoke #'1+ x))) ((5)) (6))
   ("two-local-callers" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
    (lambda (flag x) (flet ((invoke (callee v) (funcall callee v)))
      (if flag (invoke #'1+ x) (invoke #'1- x)))) ((t 5) (nil 5)) (6 4))
   ("unknown-local-caller" unresolved nil
    (lambda (flag other x) (flet ((invoke (callee v) (funcall callee v)))
      (if flag (invoke #'1+ x) (invoke other x)))) ((t 1- 5) (nil 1- 5)) (6 4))
   ("local-value-escapes" unresolved nil
    (lambda (x) (flet ((invoke (callee v) (funcall callee v)))
      (setq *escaped* #'invoke) (invoke #'1+ x))) ((5)) (6))
   ("stack-argument-position" finite ("COMMON-LISP::1+")
    (lambda (x) (flet ((invoke (callee a b c other v)
      (declare (ignore a b c other)) (funcall callee v)))
      (invoke #'1+ 10 20 30 #'1- x))) ((5)) (6))
   ("register-argument-position" finite ("COMMON-LISP::1-")
    (lambda (x) (flet ((invoke (other a b c callee v)
      (declare (ignore other a b c)) (funcall callee v)))
      (invoke #'1+ 10 20 30 #'1- x))) ((5)) (4))
   ("recursive-parameter" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
    (lambda (n) (labels ((walk (callee k) (if (zerop k) (funcall callee 10) (walk #'1- (1- k)))))
      (walk #'1+ n))) ((0) (1)) (11 9))
   ("mutual-parameters" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
    (lambda (n) (labels ((left (callee k) (if (zerop k) (funcall callee 10) (right callee (1- k))))
                        (right (callee k) (if (zerop k) (funcall callee 10) (left #'1- (1- k)))))
      (left #'1+ n))) ((0) (1) (2)) (11 11 9))
   ("assigned-parameter" unresolved nil
    (lambda (x other) (flet ((invoke (callee v) (setq callee other) (funcall callee v)))
      (invoke #'1+ x))) ((5 1-)) (4))
   ("captured-local-parameter" finite ("COMMON-LISP::1+")
    (lambda (x) (flet ((invoke (callee v)
      (let ((thunk (lambda (w) (funcall callee w)))) (funcall thunk v))))
      (invoke #'1+ x))) ((5)) (6))
   ("optional-parameter-signature" unresolved nil
    (lambda (x) (flet ((invoke (callee &optional (v 5)) (funcall callee v)))
      (invoke #'1+ x))) ((5)) (6))
   ("spread-local-call" unresolved nil
    (lambda (xs) (flet ((invoke (callee v) (funcall callee v)))
      (apply #'invoke #'1+ xs))) (((5))) (6))
   ("forwarded-parameter" finite ("COMMON-LISP::1+")
    (lambda (x) (labels ((invoke (callee v) (funcall callee v))
                        (forward (cb v) (invoke cb v))) (forward #'1+ x))) ((5)) (6))
   ("captured-lexical-prototype" lexical 1
    (lambda (x) (let* ((callee (lambda (v) (+ v 7)))
                      (thunk (lambda (v) (funcall callee v)))) (funcall thunk x))) ((5)) (12))
   ("labels-value" lexical 1
    (lambda (x) (labels ((add (v) (+ v 7)))
      (let ((callee #'add)) (funcall callee x)))) ((5)) (12))
   ("labels-recursive-value" lexical 1
    (lambda (x) (labels ((walk (v) (if (zerop v) 17
      (let ((callee #'walk)) (funcall callee (1- v)))))) (walk x))) ((0) (3)) (17 17))
   ("labels-mutual-value" lexical 1
    (lambda (x) (labels ((left (v) (let ((callee #'right)) (funcall callee v)))
                        (right (v) (+ v 11))) (left x))) ((5)) (16))
   ("labels-shadowed-value" lexical 1
    (lambda (x) (labels ((work (v) (+ v 1)))
      (flet ((invoke (v) (let ((callee #'work)) (funcall callee v))))
        (labels ((work (v) (+ v 10)))
          (+ (invoke x) (let ((callee #'work)) (funcall callee x))))))) ((5)) (21))
   ("inline-required-value" finite ("COMMON-LISP::1+")
    (lambda (x) ((lambda (callee v) (funcall callee v)) #'1+ x)) ((5)) (6))
   ("inline-default-value" finite ("COMMON-LISP::1-")
    (lambda (x) ((lambda (v &optional (callee #'1-)) (funcall callee v)) x)) ((5)) (4))
   ("inline-aux-value" finite ("COMMON-LISP::1+")
    (lambda (x) ((lambda (v &aux (first #'1+) (callee first)) (funcall callee v)) x)) ((5)) (6))
   ("inline-unknown-value" unresolved nil
    (lambda (other x) ((lambda (callee v) (funcall callee v)) other x)) ((1- 5)) (4)))))
