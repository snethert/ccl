;;; Exercise the actual native build/load entry point, with level-0 inputs only.
(in-package "CCL")
(let* ((backend (find-xload-backend :wasm32))
       (old-output (backend-xload-info-default-image-name backend))
       (compiler (backend-xload-info-compile-file-function backend))
       (out (concatenate 'string (getenv "LOADER_OUTPUT") "boot/")))
  (unwind-protect
       (progn
         (setf (backend-xload-info-default-image-name backend) out
               (backend-xload-info-compile-file-function backend)
               (lambda (source &rest options)
                 (multiple-value-bind (fasl modules warnings failure)
                     (apply compiler source options)
                   (unless (and fasl (not failure))
                     (error "Level-0 compilation failed: ~s" source))
                   (values fasl modules warnings failure))))
         (cross-xload-level-0 :wasm32 :force)
         (format t "LEVEL-0-BOOT-IMAGE-WRITTEN~%"))
    (setf (backend-xload-info-default-image-name backend) old-output
          (backend-xload-info-compile-file-function backend) compiler)))
(quit)
