;;; Read-only observation, loaded in a separate process after each clean build.
(in-package "CCL-STARTUP-CENSUS")
(defun code-hex (fn)
  (let* ((size (* 8 (ccl::%function-code-words fn)))
         (bytes (make-array size :element-type '(unsigned-byte 8))))
    (ccl::%copy-ivector-to-ivector (ccl::%function-to-function-vector fn) 0 bytes 0 size)
    (format nil "~{~2,'0x~}" (coerce bytes 'list))))
(defun module-list (fn target) (mapcar #'label-of (funcall fn target)))
(defun shared-functions ()
  (let ((rows nil) (*package* (find-package "CCL")))
    (with-open-file (s "ccl:lib;compile-ccl.lisp")
      (loop for form = (read s nil :eof) until (eq form :eof) do
        (when (and (consp form) (eq (car form) 'defun))
          (let ((name (second form)))
            (push (object "name" (label-of name) "code_hex" (code-hex (fdefinition name))) rows)))))
    (nreverse rows)))
(let* ((arches '(:ppc32 :ppc64 :x8632 :x8664 :arm))
       (targets '(:linuxppc32 :darwinppc32 :darwinppc64 :linuxppc64 :darwinx8632
                  :linuxx8664 :darwinx8664 :freebsdx8664 :solarisx8664 :win64
                  :linuxx8632 :win32 :solarisx8632 :freebsdx8632 :linuxarm :androidarm :darwinarm))
       (snap (snapshot)))
  (with-open-file (s (ccl:getenv "S1_SNAPSHOT") :direction :output :if-exists :error)
    (json (object "native" snap
      "architectures" (loop for arch in arches collect
        (object "name" (label-of arch) "compiler" (module-list #'ccl::target-compiler-modules arch)
                "xload" (module-list #'ccl::target-xload-modules arch)
                "xdev" (module-list #'ccl::target-xdev-modules arch)))
      "targets" (loop for target in targets collect
        (object "name" (label-of target) "env" (module-list #'ccl::target-env-modules target)
          "level1" (module-list #'ccl::target-level-1-modules target)
          "lib" (module-list #'ccl::target-lib-modules target)))
      "modules" (loop for entry in ccl::*ccl-system* collect
        (object "name" (label-of (car entry)) "binary" (label-of (cadr entry)) "sources" (mapcar #'label-of (caddr entry))))
      "shared_functions" (shared-functions)) s) (terpri s)))
(format t "S1-SNAPSHOT-PASS~%")
(ccl:quit)
