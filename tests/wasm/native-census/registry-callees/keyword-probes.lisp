(in-package :census-finite-probes)
(defun keyword-callee (ignored &key (fn '1+) &allow-other-keys)
  (declare (ignore ignored))
  (funcall fn 5))

(defun keyword-run ()
  (let* ((*captures* nil) (rows nil)
         (old (ccl::backend-p2-compile ccl::*host-backend*)))
    (dolist
      (spec
       '(("default" (lambda () (keyword-callee nil)) (nil) (6))
         ("supplied" (lambda () (keyword-callee nil :fn '1-)) (nil) (4))
         ("first-minus" (lambda () (keyword-callee nil :fn '1- :fn '1+)) (nil) (4))
         ("first-plus" (lambda () (keyword-callee nil :fn '1+ :fn '1-)) (nil) (6))
         ("other-key" (lambda () (keyword-callee nil :other 7 :fn '1-)) (nil) (4))
         ("stack-key" (lambda () (keyword-callee nil :p1 1 :p2 2 :p3 3 :p4 4 :fn '1-)) (nil) (4))
         ("dynamic-key" (lambda (key) (keyword-callee nil key '1-)) ((:fn)) (4))
         ("spread" (lambda (args) (apply #'keyword-callee nil args)) (((:fn 1-))) (4))))
      (destructuring-bind (name form inputs expected) spec
        (let* ((*case* name) (fn (with-observer (lambda () (compile nil form))))
               (actual (mapcar (lambda (args) (apply fn args)) inputs)))
          (unless (equal actual expected) (error "KEYWORD-NATIVE-RESULT ~s ~s" name actual))
          (push (obj "case" name "results" actual) rows))))
    (unless (eq old (ccl::backend-p2-compile ccl::*host-backend*)) (error "KEYWORD-RESTORATION"))
    (with-open-file (out (ccl:getenv "FINITE_OUTPUT") :direction :output :if-exists :error :external-format :utf-8)
      (ccl-startup-census::json
       (obj "captures" (reverse *captures*) "checks" (reverse rows)
            "snapshot" (ccl-startup-census::snapshot) "restored" :true) out)
      (terpri out))))
