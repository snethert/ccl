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
                 (let ((name (enough-namestring (truename source) (truename "ccl:"))))
                   (push (list :object (cons "file" name)) rows)
                   (format t "~&ORDERED-COMPILE ~a~%" name)
                   (multiple-value-bind (fasl modules warnings failure)
                       (apply compiler source options)
                     (setf (cdr (car rows))
                           (append (cdr (car rows))
                                   (list (cons "fasl" (and fasl (enough-namestring fasl (truename "ccl:"))))
                                         (cons "modules" (length modules))
                                         (cons "warnings" (not (null warnings)))
                                         (cons "failure" (not (null failure))))))
                     (unless (and fasl (not failure))
                       (error "Unqualified whole-file compilation: ~a" source))
                     (values fasl modules warnings failure)))))
         (let ((stop
                 (handler-case
                     ;; The shared producer cross-loads in a fresh process
                     ;; after removing sources. Avoid an earlier redundant load.
                     (progn
                       (unless (equal (getenv "LOADER_LEVEL_1") "only")
                         (cross-compile-level-0 :wasm32 t))
                       (when (getenv "LOADER_LEVEL_1")
                         (with-cross-compilation-target (:wasm32)
                           (target-xcompile-level-1 :wasm32 t)))
                       nil)
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
