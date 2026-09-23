(in-package :wasm32-compiler)

(define-condition cpl-left (error) ((payload :initarg :payload :initform 17)))
(define-condition cpl-right (warning) ())
(define-condition cpl-diamond (cpl-left cpl-right) ())
(define-condition cpl-other (error) ())

(defparameter *cpl-class-names*
  '(condition serious-condition error warning simple-condition simple-error
    type-error cpl-left cpl-right cpl-diamond cpl-other))

(defun cpl-image (name)
  (let* ((image (generic-image nil))
         (object (make-condition name)))
    (setf (svref image 1) nil
          (svref image 2) object
          (svref image 3) (mapcar (lambda (name) (cons name (find-class name)))
                                *cpl-class-names*))
    image))

(defun cpl-inputs (name)
  (when (eql (search "CORE-CPL-" (symbol-name name)) 0)
    (values (loop for class in '(cpl-diamond cpl-left cpl-right cpl-other)
                  collect (list (cpl-image class))) t)))
