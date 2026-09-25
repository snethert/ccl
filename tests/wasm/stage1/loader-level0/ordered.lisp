;;; Observe the real ordered entry point, without continuing past a failure.
(in-package "CCL")

(let* ((backend (find-xload-backend :wasm32))
       (compiler (backend-xload-info-compile-file-function backend))
       (rows nil)
       (variables *wasm32-xload-parameter-variables*)
       (before (mapcar #'symbol-value variables))
       (out (getenv "LOADER_OUTPUT")))
  (unwind-protect
       (progn
         (setf (backend-xload-info-compile-file-function backend)
               (lambda (source &rest options)
                 (let ((name (enough-namestring source (truename "ccl:"))))
                   (push (list :object (cons "file" name)) rows)
                   (format t "~&ORDERED-COMPILE ~a~%" name)
                   (multiple-value-prog1 (apply compiler source options)
                     (push (cons "compiled" t) (cdr (car rows)))))))
         (let ((stop
                 (handler-case
                     (progn (cross-xload-level-0 :wasm32 :force) nil)
                   (error (condition)
                     (list :object
                           (cons "type" (string (type-of condition)))
                           (cons "message" (format nil "~a" condition)))))))
           (assert (equal before (mapcar #'symbol-value variables)))
           (with-open-file (stream (concatenate 'string out "ordered.json")
                                   :direction :output :if-exists :supersede)
             (wasm32-json
              (list :object (cons "attempts" (reverse rows)) (cons "stop" stop)
                    (cons "host_state_restored" t)) stream)
             (terpri stream))
           (format t "~&ORDERED-OBSERVATION-COMPLETE ~s~%" stop)))
    (setf (backend-xload-info-compile-file-function backend) compiler)))
(quit)
