;;; Dedicated generation-exhaustion witness; ordinary READY keeps its budget.
(in-package "CCL")

#+wasm32-target
(let ((path "/ccl/l1-fasls/l1-sort.w32fsl"))
  ;; Bootstrap used generation one. The first reload publishes into generation
  ;; two before CCL refuses to redefine a kernel function. Further opens must
  ;; return ENOMEM through the Lisp file service, without a host exception.
  (assert (handler-case (progn (load path) nil)
            (file-error () nil)
            (error () t)))
  (dotimes (i 2)
    (assert (= (fd-open path target::os-o-rdonly) -12)))
  (flet ((load-error (name)
           (handler-case (progn (load name) :returned)
             (file-error (condition)
               (list :file-error (type-of condition)
                     (namestring (file-error-pathname condition))
                     (format nil "~a" condition)))
             (error (condition)
               (list :error (type-of condition) (format nil "~a" condition))))))
    (let* ((missing "/ccl/l1-fasls/loader-missing.w32fsl")
           (result (load-error missing)))
      (assert (equal (subseq result 0 3) (list :file-error 'simple-file-error missing)))
      (assert (search "does not exist" (fourth result))))
    (dotimes (i 2)
      (let ((result (load-error path)))
        (format t "~&LOADER-LOAD-REFUSAL ~s~%" result)
        (assert (equal (subseq result 0 3) (list :file-error 'simple-file-error path)))
        (assert (search "File operation failed" (fourth result))))))
  (format t "~&LOADER-LOAD-FILE-ERROR-PASS~%")
  (format t "~&LOADER-GENERATION-REFUSAL-PASS~%"))
