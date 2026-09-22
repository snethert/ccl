(in-package :wasm32-compiler)

;;; Callers observe native results which have no cross-target wire identity.
;;; The original definitions remain intact and are linked by their real names.
;;; NOTINLINE keeps the observed call at that definition boundary.
(defun recipe-observer (name)
  (when (single-counterpart name)
    (let ((arguments (if (member name '(ccl::%single-float-expt! ccl::%single-float-atan2!
                                         ccl::%short-float+-2! ccl::%short-float--2!
                                         ccl::%short-float*-2! ccl::%short-float/-2!))
                         '(x y) '(x))))
      (return-from recipe-observer
        `(lambda ,arguments
           (declare (notinline ,name))
           (let ((destination (ccl::%make-sfloat)))
             (,name ,@arguments destination))))))
  (when (member name '(ccl::%remove-direct-methods ccl::%do-remove-direct-method))
    (return-from recipe-observer
      `(lambda (objects)
         (declare (notinline ,name))
         (let ((method (svref objects 0)) (class (svref objects 1))
               (other (svref objects 2)))
           (setf (ccl::%method.specializers method) (list class)
                 (ccl::specializer.direct-methods class) (list method other))
           (core-collect)
           ,(if (eq name 'ccl::%remove-direct-methods)
                `(,name method) `(,name class method))
           (core-collect)
           (values (eq (car (ccl::specializer.direct-methods class)) other)
                   (null (cdr (ccl::specializer.direct-methods class)))
                   (eq (car (ccl::%method.specializers method)) class))))))
  (when (member name '(ccl::%defgeneric-keys ccl::%set-defgeneric-keys))
    (return-from recipe-observer
      `(lambda (gf keys)
         (declare (notinline ,name))
         (let ((saved (ccl::gf.dispatch-table gf))
               (table (vector nil nil nil 0 gf 0 nil nil)))
           (unwind-protect
               (progn
                 (setf (ccl::gf.dispatch-table gf) table)
                 ,(if (eq name 'ccl::%defgeneric-keys)
                      '(setf (ccl::%gf-dispatch-table-keyvect table) keys))
                 (core-collect)
                 (let ((result ,(if (eq name 'ccl::%defgeneric-keys)
                                    `(,name gf) `(,name gf keys))))
                   (core-collect)
                   (values (eq result keys)
                           (eq (ccl::%gf-dispatch-table-keyvect table) keys)
                           result)))
             (setf (ccl::gf.dispatch-table gf) saved))))))
  (case name
    (ccl::%non-standard-instance-slots
     '(lambda (gf)
        (declare (notinline ccl::%non-standard-instance-slots))
        (let ((slots (ccl::%non-standard-instance-slots gf (ccl::typecode gf))))
          (core-collect)
          (values (ccl::%svref slots 1) (ccl::%svref slots 2) (ccl::%svref slots 3)))))
    (ccl::multi-method-index
     '(lambda (objects)
        (declare (notinline ccl::multi-method-index))
        (let* ((method (svref objects 0))
               (ccl::*t-class* (svref objects 1))
               (specializer (car (ccl::%method.specializers method)))
               (specializers nil))
          (dolist (flag (svref objects 2))
            (push (if flag specializer ccl::*t-class*) specializers))
          (setf (ccl::%method.specializers method) (ccl::list-nreverse specializers))
          (core-collect)
          (ccl::multi-method-index method))))
    (ccl::non-dt-dcode-function
     '(lambda (gf found)
        (declare (notinline ccl::non-dt-dcode-function))
        (let ((events nil)
              (saved ccl::*non-dt-dcode-functions*))
          (unwind-protect
              (progn
                (setq ccl::*non-dt-dcode-functions*
                      (list (lambda (object) (declare (ignore object))
                              (push :first events) (core-collect) nil)
                            (lambda (object)
                              (push :second events) (core-collect) (if found object))
                            (lambda (object) (declare (ignore object))
                              (push :third events) (core-collect) nil)))
                (let ((result (ccl::non-dt-dcode-function gf)))
                  (values (eq result gf) events)))
            (setq ccl::*non-dt-dcode-functions* saved)))))
    (ccl::%clear-class-primary-slot-accessor-offsets
     '(lambda (class)
        (declare (notinline ccl::%clear-class-primary-slot-accessor-offsets))
        (let* ((saved (ccl::%class.alist class))
               (first (ccl::%cons-slot-accessor-info class :first 7))
               (second (ccl::%cons-slot-accessor-info class :second 19)))
          (unwind-protect
              (progn
                (setf (ccl::%class.alist class)
                      (cons (cons 'ccl::%class-primary-slot-accessor-info (list first second)) saved))
                (core-collect)
                (ccl::%clear-class-primary-slot-accessor-offsets class)
                (core-collect)
                (values (null (ccl::%slot-accessor-info.offset first))
                        (null (ccl::%slot-accessor-info.offset second))
                        (eq (ccl::%slot-accessor-info.class first) class)
                        (eq (ccl::%slot-accessor-info.class second) class)))
            (setf (ccl::%class.alist class) saved)))))
    (ccl::instance-slots
     '(lambda (instance)
        (declare (notinline ccl::instance-slots))
        (let ((slots (ccl::instance-slots instance)))
          (core-collect)
          (values (eq (ccl::%svref slots 0) instance)
                  (ccl::uvsize slots) (ccl::%svref slots 1)))))
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
