;;; Reconstruct only from saved FASLs, after both fixture sources were deleted.
(in-package :wasm32-compiler)
(let* ((out (ccl:getenv "LOADER_OUTPUT"))
       (fasls (mapcar (lambda (name) (concatenate 'string out name ".w32fsl"))
                      '("p2-0" "p2-0-second")))
       (variables ccl::*wasm32-xload-parameter-variables*)
       (before (mapcar #'symbol-value variables)))
  (let ((result (apply #'ccl::wasm32-xfasload out fasls)))
    (assert (equal before (mapcar #'symbol-value variables)))
    (format t "CROSS-LOAD-PASS ~s~%" result))
  ;; A failed load must restore the same target globals as a successful load.
  (assert (handler-case
              (progn (ccl::wasm32-xfasload out (concatenate 'string out "missing.w32fsl")) nil)
            (simple-error (e) (string= (format nil "~a" e) "Error #-2"))))
  (assert (equal before (mapcar #'symbol-value variables)))
  (assert (= 3 (funcall (compile nil '(lambda (x) (+ x 1))) 2)))
  (format t "HOST-STATE-RESTORED-PASS~%"))
(ccl:quit)
