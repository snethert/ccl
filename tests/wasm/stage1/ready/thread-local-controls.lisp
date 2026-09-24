(in-package :wasm32-compiler)

(with-open-file (stream (ccl:getenv "VALIDATION_PROBE_DRIVER"))
  (loop for form = (read stream nil :eof) until (eq form :eof)
        when (and (consp form) (eq (car form) 'defun)
                  (eq (second form) 'validation-image-callee-p))
          do (eval form) (return)))
(let* ((image (cpl-image 'cpl-left))
       (cases (list (list 'entry (list (list image)))))
       (protocol (svref image 8)))
  (assert (validation-image-callee-p 'close cases))
  (assert (not (validation-image-callee-p 'close nil)))
  (assert (not (validation-image-callee-p
                'close (list (list 'entry (list (list (make-array 13))))))))
  (assert (not (validation-image-callee-p 'ccl:getenv cases)))
  (unwind-protect
      (progn
        (setf (svref image 8) (remove #'close protocol))
        (assert (not (validation-image-callee-p 'close cases))))
    (setf (svref image 8) protocol)))
(format t "READY-IMAGE-CALLEE-CONTROLS-PASS~%")

(dolist (arguments '(() (nil nil)))
  (let ((answer
          (handler-case
              (progn
                (call-with-target
                 (lambda ()
                   (compile-bootstrap-form
                    `(defun thread-local-arity ()
                       (ccl::%wasm-thread-local-value ,@arguments))
                    "thread_local_arity" nil)))
                :admitted)
            (unsupported-wasm32-code (condition)
              (unsupported-operation condition)))))
    (assert (eq answer :thread-local-value-arity))))
(format t "THREAD-LOCAL-ARITY-PASS~%")
(ccl:quit)
