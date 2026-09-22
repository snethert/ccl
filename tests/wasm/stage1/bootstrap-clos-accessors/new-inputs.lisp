(in-package :wasm32-compiler)

(defclass introspection-instance () ((value :initarg :value)))
(defvar *class-inputs* (make-hash-table :test #'eq))

(defun class-input (value)
  (let ((instance (make-instance 'introspection-instance :value value)))
    (setf (gethash instance *class-inputs*) t)
    instance))

(defun class-projection (instance)
  (let* ((wrapper (ccl::instance.class-wrapper instance))
         (class (ccl::%wrapper-class wrapper)))
    (assert (eq class (class-of instance)))
    (assert (eq (ccl::%class.own-wrapper class) wrapper))
    (assert (eq (ccl::slot-vector.instance (ccl::instance.slots instance)) instance))
    (vector (ccl::%class.name class) (ccl::%wrapper-instance-slots wrapper)
            (ccl::%svref (ccl::instance.slots instance) 1)
            (cons (ccl::istruct-type-name wrapper) nil)
            (ccl::uvsize (ccl::instance.slots class)))))

(defvar *slot-inputs* (make-hash-table :test #'eq))

(defun slot-input (name documentation)
  (let ((slot (make-instance 'ccl::standard-direct-slot-definition
                            :name name :type 'integer :initargs (list name)
                            :initform 17 :initfunction nil :allocation :instance
                            :documentation documentation
                            :readers (list name) :writers (list (list 'setf name)))))
    (setf (slot-value slot 'class) nil
          (gethash slot *slot-inputs*) t)
    slot))

(defun slot-projection (slot)
  ;; Getter fixtures need the real slot fields, not an entire cyclic CLOS
  ;; image. The wrapper and slots backpointer are explicitly outside this
  ;; projection and no credited getter reads them.
  (let ((slots (let ((v (ccl::instance.slots slot)))
                 (coerce (loop for i below (ccl::uvsize v) collect (ccl::%svref v i)) 'vector))))
    (let ((fields (gethash slot *slot-inputs*)))
      (dotimes (i (length slots))
        (when (or (zerop i) (and (listp fields) (not (member i fields))))
          (setf (svref slots i) nil))))
    slots))

(defun single-counterpart (name)
  (let ((text (symbol-name name)))
    (cond ((member text '("%SHORT-FLOAT+-2!" "%SHORT-FLOAT--2!"
                         "%SHORT-FLOAT*-2!" "%SHORT-FLOAT/-2!") :test #'equal)
           (cdr (assoc name '((ccl::%short-float+-2! . +)
                              (ccl::%short-float--2! . -)
                              (ccl::%short-float*-2! . *)
                              (ccl::%short-float/-2! . /)))))
          ((and (eql (search "%SINGLE-FLOAT-" text) 0)
                (char= (char text (1- (length text))) #\!))
           (intern (subseq text 0 (1- (length text))) "CCL")))))

(load (merge-pathnames "clos-inputs.lisp" *load-pathname*))

(defun new-inputs (name)
  (multiple-value-bind (inputs covered) (clos-accessor-inputs name)
    (when covered (return-from new-inputs (values inputs t))))
  (let ((s (symbol-name name)))
    (cond ((member s '("CORE-LEXPR-LIST" "CORE-LEXPR-VALUES"
                       "CORE-LEXPR-NESTED" "CORE-LEXPR-LOCAL") :test #'equal)
           (values '(nil (17) (nil 1 (2 . 3) "four" 5) (1 2 3 4 5 6 7)) t))
          ((member s '("CORE-LEXPR-PREFIX" "CORE-LEXPR-EFFECTS"
                       "CORE-LEXPR-CLEANUP") :test #'equal)
           (values '((17) ((1 . 2) nil 3 "four" 5) (1 2 3 4 5 6 7)) t))
          ((and (>= (length s) 15) (string= "CORE-CONDITION-" s :end2 15))
           (values '((nil) (17) ((1 . 2)) ("payload")) t))
          ((equal s "STREAM-IS-CLOSED")
           (values '((nil) (17) ((1 . 2))) t))
          ((equal s "SIGNAL-PACKAGE-ERROR")
           (values '((:package "bad package") (:package "bad ~s" 17)) t))
          ((equal s "CORE-CLASS-LAYOUT")
           (values (mapcar (lambda (x) (list (class-input x))) '(nil 17 (1 . 2))) t))
          ((equal s "LFUN-KEYVECT")
           (values (mapcar (lambda (n) (list (core-native-function n)))
                           '(core-key-none core-key-rest core-key-empty
                             core-key-one core-key-alias)) t))
          ((equal s "CORE-KEY-NONE") (values '((7)) t))
          ((equal s "CORE-KEY-REST") (values '(() (1 2 3)) t))
          ((equal s "CORE-KEY-EMPTY") (values '(()) t))
          ((equal s "CORE-KEY-ONE") (values '(() (:a 7)) t))
          ((equal s "CORE-KEY-ALIAS") (values '(() (:renamed 7 :b 9)) t))
          ((member s '("CORE-KEY-CLOSURE" "CORE-KEY-ORDER") :test #'equal)
           (values '((nil) (7) ((1 . 2))) t))
          ((member s '("%SLOT-DEFINITION-NAME" "%SLOT-DEFINITION-TYPE"
                       "%SLOT-DEFINITION-INITARGS" "%SLOT-DEFINITION-INITFORM"
                       "%SLOT-DEFINITION-INITFUNCTION" "%SLOT-DEFINITION-ALLOCATION"
                       "%SLOT-DEFINITION-CLASS" "%SLOT-DEFINITION-DOCUMENTATION"
                       "%SLOT-DEFINITION-READERS" "%SLOT-DEFINITION-WRITERS") :test #'equal)
           (values (list (list (slot-input :first "first slot"))
                         (list (slot-input :second nil))) t))
          ((member s '("%SHORT-FLOAT+-2!" "%SHORT-FLOAT--2!"
                       "%SHORT-FLOAT*-2!" "%SHORT-FLOAT/-2!") :test #'equal)
           (values '((1.5s0 2.0s0) (-7.0s0 3.0s0)
                     (-0.0s0 2.0s0) (1.0s10 1.0s-10)) t))
          ((member s '("%SINGLE-FLOAT-EXPT!" "%SINGLE-FLOAT-ATAN2!") :test #'equal)
           (values '((1.0s0 2.0s0) (4.0s0 0.5s0)
                     (2.0s0 3.0s0)) t))
          ((member s '("%SINGLE-FLOAT-SIN!" "%SINGLE-FLOAT-COS!"
                       "%SINGLE-FLOAT-TAN!" "%SINGLE-FLOAT-ATAN!"
                       "%SINGLE-FLOAT-SINH!" "%SINGLE-FLOAT-COSH!"
                       "%SINGLE-FLOAT-TANH!" "%SINGLE-FLOAT-EXP!"
                       "%SINGLE-FLOAT-LOG!" "%SINGLE-FLOAT-ASINH!"
                       "%SINGLE-FLOAT-ACOSH!" "%SINGLE-FLOAT-ATANH!"
                       "%SINGLE-FLOAT-ACOS!" "%SINGLE-FLOAT-ASIN!") :test #'equal)
           ;; Exact identities are native-compatible execution witnesses;
           ;; the separately accepted libm corpus covers finite ULP differences.
           (values (list (list (cond ((search "ACOSH" s) 1.0s0)
                                     ((search "LOG" s) 1.0s0)
                                     ((search "ACOS" s) 1.0s0)
                                     (t 0.0s0)))) t))
          ((member s '("%DOUBLE-FLOAT-ASINH!" "%DOUBLE-FLOAT-ACOSH!"
                       "%DOUBLE-FLOAT-ATANH!") :test #'equal)
           (values (list (list (if (search "ACOSH" s) 1.0d0 0.0d0) 99.0d0)) t))
          (t (values nil nil)))))
