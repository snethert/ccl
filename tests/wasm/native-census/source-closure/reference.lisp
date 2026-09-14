;;; Native comparison with no FCOMP/pass-2/effect/reader observation wrappers.
(in-package :ccl-source-closure)
(defun reference ()
  (let* ((path (pathname (ccl:getenv "CCL_CLOSURE_SOURCE")))
         (ccl::*target-backend* ccl::*host-backend*)
         (ccl::*fasl-target* (ccl::backend-name ccl::*host-backend*))
         (*features* (ccl::setup-target-features ccl::*host-backend* *features*))
         (outputs (ccl::with-cross-compilation-target ((ccl::backend-name ccl::*host-backend*))
                    (compile-input path)))
         (rows nil))
    (loop for row in outputs for index from 0 do
      (when (member (car row) '(4 35 37))
        (unless (functionp (second row)) (error "REFERENCE-FUNCTION-OUTPUT"))
        (push (obj "index" index "opcode" (car row)
                   "name" (label (second row)) "code" (native-code (second row))) rows)))
    (with-open-file (out (ccl:getenv "CCL_CLOSURE_OUTPUT") :direction :output :if-exists :error
                         :external-format :utf-8)
      (ccl-startup-census::json
        (obj "output_opcodes" (mapcar #'car outputs) "functions" (nreverse rows)
             "observation_wrappers" :false "fasl_written" :false) out)
      (terpri out))))
