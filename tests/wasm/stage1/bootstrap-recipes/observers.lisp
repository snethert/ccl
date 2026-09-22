(in-package :wasm32-compiler)

;;; Callers observe native results which have no cross-target wire identity.
;;; The original definitions remain intact and are linked by their real names.
;;; NOTINLINE keeps the observed call at that definition boundary.
(defun recipe-observer (name)
  (case name
    (ccl::make-numeric-ctype-predicate
     '(lambda (ctype inputs)
        (declare (notinline ccl::make-numeric-ctype-predicate))
        (let ((predicate (ccl::make-numeric-ctype-predicate ctype)))
          (core-collect)
          (if predicate
            (let ((answers nil))
              (dolist (input inputs (ccl::list-nreverse answers))
                (push (funcall predicate input) answers)))
            :no-predicate))))
    (ccl::%array-header-subtype
     '(lambda (array)
        (declare (notinline ccl::%array-header-subtype))
        (= (ccl::%array-header-subtype array)
           (ccl::typecode (ccl::%svref array 2)))))
    (ccl::array-element-subtype
     '(lambda (array data)
        (declare (notinline ccl::array-element-subtype))
        (= (ccl::array-element-subtype array) (ccl::typecode data))))
    (ccl::array-data-offset-subtype
     '(lambda (array)
        (declare (notinline ccl::array-data-offset-subtype))
        (multiple-value-bind (data offset subtype)
            (ccl::array-data-offset-subtype array)
          (values data offset (= subtype (ccl::typecode data))))))
    (ccl::%set-simple-array-p
     '(lambda (array)
        (declare (notinline ccl::%set-simple-array-p))
        (ccl::%set-simple-array-p array)
        (ccl::simple-array-p array)))
    (ccl::%array-index
     '(lambda (array ccl::&lexpr indices)
        (declare (notinline ccl::%array-index))
        (let ((index (ccl::%array-index array indices (ccl::%lexpr-count indices) t)))
          (list index :indexed))))
    (ccl::toplevel
     '(lambda () (declare (notinline ccl::toplevel)) (catch :toplevel (ccl::toplevel) :returned-without-throw)))
    (ccl::undefine-constant
     '(lambda (symbol value)
        (declare (notinline ccl::undefine-constant))
        (ccl::%set-sym-global-value symbol value)
        (let ((before (boundp symbol)))
          (ccl::undefine-constant symbol)
          (values before (boundp symbol)))))))
