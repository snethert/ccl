;;; Actual COMPILE-FILE and LOAD, with a temporary forwarding backend observer.
(defpackage :ccl-deferred-probes (:use :cl))
(in-package :ccl-deferred-probes)
(defclass box () ((left :initarg :left)))

(defun record-value (name actual expected)
  (unless (equal actual expected) (error "DEFERRED-VALUE ~s ~s /= ~s" name actual expected))
  (ccl-complete-census::emit "deferred-value" "case" name "matches" :true))

(defun compile-input (input output observed)
  (let* ((backend ccl::*host-backend*) (original (ccl::backend-p2-compile backend))
         (*gensym-counter* 100000))
    (unwind-protect
      (progn
        (when observed
          (setf (ccl::backend-p2-compile backend)
            (lambda (afunc &rest args)
              (let ((*gensym-counter* *gensym-counter*))
                (ccl-complete-census::observe :before-pass2 afunc))
              (multiple-value-prog1 (apply original afunc args)
                (let ((*gensym-counter* *gensym-counter*))
                  (ccl-complete-census::observe :function-materialized afunc))))))
        (multiple-value-bind (file warnings failure)
            (compile-file input :output-file output :verbose nil :print nil)
          (declare (ignore warnings))
          (unless (and file (not failure)) (error "DEFERRED-COMPILE-FAILURE"))))
      (setf (ccl::backend-p2-compile backend) original))
    (unless (eq original (ccl::backend-p2-compile backend)) (error "DEFERRED-BACKEND-NOT-RESTORED"))))

(defun run ()
  (let* ((directory (ccl:getenv "CCL_DEFERRED_OUTPUT"))
         (input (ccl:getenv "CCL_DEFERRED_INPUT"))
         (reference (concatenate 'string directory "/reference.dx64fsl"))
         (observed (concatenate 'string directory "/observed.dx64fsl")))
    (compile-input input reference nil)
    (ccl-complete-census::with-build-observation
      (concatenate 'string directory "/build.jsonl")
      (concatenate 'string directory "/registries.jsonl")
      (lambda ()
        ;; This is explicitly a read of the real token, not a claimed store.
        (ccl-complete-census::emit "deferred-marker-read"
          "symbol" (ccl-startup-census::dependency-id ccl::cfasl-load-time-eval-sym)
          "macro" (ccl-rich-census::describe-value (fboundp ccl::cfasl-load-time-eval-sym)))
        (compile-input input observed t)
        (load observed :verbose nil :print nil)
        (dolist (name '(read-left class-object shared-list callable-result nested-value))
          (ccl-complete-census::emit "deferred-loaded"
            "name" (symbol-name name) "function" (ccl-complete-census::function-id (fdefinition name))))
        (record-value "slot-value" (read-left (make-instance 'box :left 43)) 43)
        (record-value "class-cell" (eq (class-object) (find-class 'box)) t)
        (record-value "list-value" (shared-list) '(:retained :data))
        (record-value "retained-object" (eq (shared-list) (shared-list)) t)
        (record-value "callable-value" (funcall (callable-result) 9) 10)
        (record-value "nested-initializer" (nested-value) '((:nested)))
        (ccl-complete-census::drain-functions)))
    (format t "DEFERRED-NATIVE-PASS~%")))
