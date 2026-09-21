;;; These are collector controls, not additions to the original-definition count.
(in-package :wasm32-compiler)

(defun core-collect () nil)

(defun core-probe-forms ()
  '((defun core-access (x i) (ccl::%svref x i))
    (defun core-struct-access (x) (ccl::struct-ref x 0))
    (defun core-slot-access (x) (ccl::%slot-ref x 0))
    (defun core-node-size () target::node-size)
    (defun core-gvector (x)
      (ccl::%gvector target::subtag-simple-vector x (progn (core-collect) x)))
    (defun core-ref (x)
      (ccl::%svref x (progn (core-collect) 1)))
    (defun core-set (x y)
      (ccl::%svset x (progn (core-collect) 0)
                  (progn (core-collect) y))
      x)
    (defun core-struct (x)
      (let ((structure (ccl::%gvector target::subtag-struct nil x)))
        (core-collect)
        (ccl::struct-ref structure 1)))
    (defun core-slot (x)
      (ccl::%slot-ref (ccl::%gvector target::subtag-slot-vector x)
                     (progn (core-collect) 0)))
    (defun core-cleanup (x)
      (unwind-protect
          (ccl::%gvector target::subtag-simple-vector x x)
        (core-collect)))
    (defun core-transfer (x)
      (catch 'done
        (ccl::%gvector target::subtag-simple-vector
                      x (progn (core-collect) (throw 'done x)))))))

(defun core-add-probes (native-forms)
  (dolist (form (cons '(defun core-collect () nil) (core-probe-forms)))
    (let* ((name (second form))
           (wire (if (eq name 'core-collect) "collector_probe"
                     (string-downcase (substitute #\_ #\- (symbol-name name)))))
           (result (call-with-target (lambda () (compile-bootstrap-form form wire nil)))))
      (setf (getf result :source-name) name)
      (push (list form result) *core-candidates*)
      (setf (gethash name *core-native-functions*)
            (ccl::compile-named-function
             (bootstrap-function-form (if (eq name 'core-collect) form
                                        (find name native-forms :key #'second))) :name name)))))
