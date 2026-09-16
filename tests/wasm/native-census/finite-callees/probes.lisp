;;; Native pass-1 probes. Temporary pass-2 observer always forwards and restores.
(defpackage :census-finite-probes (:use :cl))
(in-package :census-finite-probes)
(defvar *captures* nil)
(defvar *case* nil)
(defvar *effect* 0)
(defparameter *probes*
  '(("function-cell" finite ("COMMON-LISP::1+")
     (lambda (x) (let ((callee #'1+)) (funcall callee x))) ((5)) (6))
    ("if-functions" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
     (lambda (flag x) (let ((callee (if flag #'1+ #'1-))) (funcall callee x))) ((t 5) (nil 5)) (6 4))
    ("if-symbols" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
     (lambda (flag x) (let ((callee (if flag '1+ '1-))) (funcall callee x))) ((t 5) (nil 5)) (6 4))
    ("if-closures" lexical 2
     (lambda (flag x) (let ((callee (if flag (lambda (v) (+ v 2)) (lambda (v) (- v 3)))))
                       (funcall callee x))) ((t 5) (nil 5)) (7 2))
    ("alias-chain" finite ("COMMON-LISP::1+")
     (lambda (x) (let* ((first #'1+) (callee first)) (funcall callee x))) ((5)) (6))
    ("nested-let" finite ("COMMON-LISP::1+" "COMMON-LISP::1-")
     (lambda (flag x) (let ((callee (let ((p flag)) (if p #'1+ #'1-)))) (funcall callee x)))
     ((t 5) (nil 5)) (6 4))
    ("progn-last" finite ("COMMON-LISP::1+")
     (lambda (x) (let ((callee (progn (incf *effect*) #'1+))) (funcall callee x))) ((5)) (6))
    ("prog1-first" finite ("COMMON-LISP::1+")
     (lambda (x) (let ((callee (prog1 #'1+ (incf *effect*)))) (funcall callee x))) ((5)) (6))
    ("values-primary" finite ("COMMON-LISP::1+")
     (lambda (x) (let ((callee (values #'1+ #'1-))) (funcall callee x))) ((5)) (6))
    ("parameter" unresolved nil
     (lambda (callee x) (funcall callee x)) ((1+ 5)) (6))
    ("unknown-if-branch" unresolved nil
     (lambda (flag other x) (let ((callee (if flag #'1+ other))) (funcall callee x)))
     ((t 1- 5) (nil 1- 5)) (6 4))
    ("assigned" unresolved nil
     (lambda (other x) (let ((callee #'1+)) (setq callee other) (funcall callee x))) ((1- 5)) (4))
    ("captured-write" unresolved nil
     (lambda (other x) (let ((callee #'1+))
       (flet ((change () (setq callee other))) (change) (funcall callee x)))) ((1- 5)) (4))
    ("shadowed-parameter" unresolved nil
     (lambda (callee x) (let* ((result (funcall callee x)) (callee #'1+))
       (declare (ignore callee)) result)) ((1- 5)) (4))
    ("unknown-or" unresolved nil
     (lambda (other x) (let ((callee (or other #'1+))) (funcall callee x))) ((nil 5) (1- 5)) (6 4))))

(defun obj (&rest args) (apply #'ccl-startup-census::object args))
(defun with-observer (thunk)
  (let* ((backend ccl::*host-backend*) (old (ccl::backend-p2-compile backend))
         (owner ccl:*current-process*))
    (unwind-protect
      (progn
        (setf (ccl::backend-p2-compile backend)
          (lambda (afunc &rest args)
            (unless (eq owner ccl:*current-process*) (error "FINITE-OBSERVER-OWNER"))
            (push (obj "case" *case* "function" (ccl-startup-census::function-observation afunc)
                       "ir" (ccl-rich-census::describe-value afunc)) *captures*)
            (apply old afunc args)))
        (funcall thunk))
      (setf (ccl::backend-p2-compile backend) old))))

(defun run ()
  (let* ((*captures* nil) (*effect* 0) (rows nil)
         (backend ccl::*host-backend*) (old (ccl::backend-p2-compile backend)) (tag (gensym)))
    (unless (eq :escaped (catch tag (with-observer (lambda () (throw tag :escaped)))))
      (error "FINITE-NONLOCAL-EXIT"))
    (unless (eq old (ccl::backend-p2-compile backend)) (error "FINITE-NONLOCAL-RESTORATION"))
    (dolist (spec *probes*)
      (destructuring-bind (name status targets form inputs expected) spec
        (let* ((*case* name) (fn (with-observer (lambda () (compile nil form))))
               (actual (mapcar (lambda (args) (apply fn args)) inputs)))
          (unless (equal actual expected) (error "FINITE-NATIVE-RESULT ~s ~s" name actual))
          (push (obj "name" name "status" (symbol-name status) "targets" targets
                     "results" actual) rows))))
    (unless (and (eq old (ccl::backend-p2-compile backend)) (= *effect* 2))
      (error "FINITE-NORMAL-RESTORATION-OR-EFFECT"))
    (with-open-file (out (ccl:getenv "FINITE_OUTPUT") :direction :output :if-exists :error :external-format :utf-8)
      (ccl-startup-census::json
        (obj "version" 1 "captures" (reverse *captures*) "checks" (reverse rows)
             "snapshot" (ccl-startup-census::snapshot) "restored" :true "effects" *effect*) out)
      (terpri out))))
