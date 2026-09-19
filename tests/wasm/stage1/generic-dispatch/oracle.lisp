(in-package :wasm32-compiler)
(defgeneric native_route (x))
(defvar *gd-trace* nil)
(defun gd-native-values (gf x &optional required-protocol)
  (coerce
    (multiple-value-list
      (handler-case
        (if required-protocol (no-applicable-method gf x) (funcall gf x))
        (ccl::no-applicable-method-exists (c)
          (assert (typep c 'error))
          (values 901 (eq (slot-value c 'ccl::gf) gf) (car (slot-value c 'ccl::args))))))
    'vector))
(let ((rows nil))
  (dolist (encapsulated '(nil t))
    (dolist (method (copy-list (ccl:generic-function-methods #'native_route))) (remove-method #'native_route method))
    (eval '(defmethod native_route ((x t)) (declare (ignore x)) (values 10 11)))
    (when encapsulated (eval '(ccl:advise native_route (push 1 *gd-trace*) :when :before :name gd)))
    (let* ((gf #'native_route) (before (gd-native-values gf 3)))
      (assert (eq (not (null (ccl::function-encapsulated-p gf))) encapsulated))
      (eval '(defmethod native_route ((x (eql 3))) (declare (ignore x)) (values 20 21)))
      (let ((specific (gd-native-values gf 3)) (miss (gd-native-values gf 9)))
        (remove-method gf (find-method gf nil (list (ccl:intern-eql-specializer 3))))
        (let ((remaining (gd-native-values gf 3)))
          (remove-method gf (find-method gf nil (list (find-class 't))))
          (assert (null (ccl:generic-function-methods gf)))
          (let ((defect (gd-native-values gf 3)) (required (gd-native-values gf 3 t)))
            (assert (equalp defect #(10 11)))
            (assert (equalp required #(901 t 3)))
            ;; The standard NO-APPLICABLE-METHOD protocol offers CONTINUE.
            (let ((resumed
                    (coerce (multiple-value-list
                     (handler-bind ((ccl::no-applicable-method-exists
                                      (lambda (c) (declare (ignore c))
                                        (eval '(defmethod native_route ((x t)) (declare (ignore x)) (values 30 31)))
                                        (invoke-restart 'continue))))
                       (no-applicable-method gf 3))) 'vector)))
              (push (vector encapsulated before specific miss remaining defect required resumed) rows))))))
    (when encapsulated (eval '(ccl:unadvise native_route :name gd))))
  (with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "native-behavior.json") :direction :output :if-exists :error)
    (write-pool-graph s (nreverse rows))))

;; Reverse insertion and replacement are measured on a real native GF.
(dolist (method (copy-list (ccl:generic-function-methods #'native_route))) (remove-method #'native_route method))
(eval '(defmethod native_route ((x (eql 3))) (declare (ignore x)) (values 20 21)))
(let ((gf #'native_route))
 (let ((specific (gd-native-values gf 3)) (miss (gd-native-values gf 9)))
  (eval '(defmethod native_route ((x t)) (declare (ignore x)) (values 10 11)))
  (let ((ordered (gd-native-values gf 3)))
   (eval '(defmethod native_route ((x (eql 3))) (declare (ignore x)) (values 30 31)))
   (with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "native-order.json") :direction :output :if-exists :error)
    (write-pool-graph s (list (vector specific miss ordered (gd-native-values gf 3))))))))

(let* ((gf #'native_route) (cell (cons 0 nil))
       (cleanup (coerce (multiple-value-list
         (handler-case (unwind-protect (no-applicable-method gf 3) (rplaca cell 71))
           (ccl::no-applicable-method-exists (c)
             (values 901 (eq (slot-value c 'ccl::gf) gf) (car (slot-value c 'ccl::args)) (car cell))))) 'vector))
       (resignal (coerce (multiple-value-list
         (handler-case
           (handler-bind ((ccl::no-applicable-method-exists (lambda (c) (error c))))
             (no-applicable-method gf 3))
           (ccl::no-applicable-method-exists (c)
             (values 901 (eq (slot-value c 'ccl::gf) gf) (car (slot-value c 'ccl::args)))))) 'vector))
       (arity (coerce (multiple-value-list (handler-case (funcall gf) (program-error () 902))) 'vector)))
 (with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "native-flow.json") :direction :output :if-exists :error)
  (write-pool-graph s (list (vector cleanup resignal arity)))))
