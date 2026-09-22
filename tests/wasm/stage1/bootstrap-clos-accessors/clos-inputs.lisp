(in-package :wasm32-compiler)

(defvar *accessor-function-names* (make-hash-table :test #'eq))

;;; These are real native CLOS objects. Only the stated slots are transported;
;;; their instance backpointer is reconstructed, not replaced with NIL.
(defun accessor-instance (instance fields)
  (setf (gethash instance *slot-inputs*) fields)
  instance)

(defun accessor-class (name)
  (accessor-instance (make-instance 'standard-class :name name)
                     (list ccl::%class.name)))

(defun accessor-class-input (kind value)
  (let ((class (accessor-class :accessor-class)))
    (ecase kind
      (:alist
       (setf (ccl::%class.alist class) value
             (gethash class *slot-inputs*) (list ccl::%class.name ccl::%class.alist)))
      (:supers
       (setf (ccl::%class.local-supers class)
             (if value (list (accessor-class :first-super) (accessor-class :second-super)))
             (gethash class *slot-inputs*) (list ccl::%class.name ccl::%class.local-supers)))
      (:subs
       (setf (ccl::%class.subclasses class)
             (if value (list (accessor-class :first-child) (accessor-class :second-child)))
             (gethash class *slot-inputs*) (list ccl::%class.name ccl::%class.subclasses))))
    class))

(defun accessor-method (qualifiers)
  (let* ((class (accessor-class :specializer))
         (gf (funcallable-input :associated-gf))
         (function (ccl::compile-named-function
                     '(lambda (method-context x) (declare (ignore method-context)) x)
                     :name 'core-method-body))
         (method (make-instance 'standard-method :qualifiers qualifiers
                                :specializers (list class) :lambda-list '(x)
                                :function function)))
    (setf (gethash function *accessor-function-names*) 'core-method-body
          (ccl::%method.gf method) gf
          (ccl::%method.name method) 'accessor-method-name)
    (accessor-instance method '(1 2 3 4 5 6))))

(defun accessor-effective-slot (name location)
  (let ((slot (make-instance 'ccl::standard-effective-slot-definition
                            :name name :type 'integer :initargs (list name)
                            :initform 17 :initfunction nil :allocation :instance)))
    (setf (ccl::standard-effective-slot-definition.location slot) location)
    (accessor-instance slot (list ccl::standard-slot-definition.name
                                 ccl::standard-slot-definition.type
                                 ccl::standard-effective-slot-definition.location))))

(defun clos-accessor-inputs (name)
  (case name
    ((ccl::%method-qualifiers ccl::%method-specializers ccl::%method-function
      ccl::%method-gf ccl::%method-name ccl::%method-lambda-list)
     (values (mapcar (lambda (qualifiers) (list (accessor-method qualifiers)))
                    '(nil (:before) (:around))) t))
    (ccl::%class-alist
     (values (mapcar (lambda (value) (list (accessor-class-input :alist value)))
                    '(nil ((:first . 17)) ((:first . nil) (:second 3 4)))) t))
    (ccl::%class-direct-superclasses
     (values (mapcar (lambda (value) (list (accessor-class-input :supers value))) '(nil t)) t))
    (ccl::%class-direct-subclasses
     (values (mapcar (lambda (value) (list (accessor-class-input :subs value))) '(nil t)) t))
    (ccl::%class-get
     (values (loop for key in '(:first :second :missing) append
               (loop for default in '(nil :default) collect
                 (list (accessor-class-input :alist '((:first . 17) (:second . nil))) key default))) t))
    (ccl::%slot-definition-location
     (values (mapcar (lambda (value) (list (accessor-effective-slot :value value)))
                    '(0 1 13 (:shared . 42))) t))
    (ccl::find-slotd
     (values (loop for name in '(:first :second :missing) collect
               (list name (list (accessor-effective-slot :first 1)
                                (accessor-effective-slot :second 2)
                                (accessor-effective-slot :first 3)))) t))
    ((ccl::%remove-direct-methods ccl::%do-remove-direct-method)
     (values (loop for qualifiers in '(nil (:before) (:around)) collect
               (let ((class (accessor-class :specializer)))
                 (setf (gethash class *slot-inputs*) (list 1 ccl::%class.name))
                 (list (vector (accessor-method qualifiers) class
                               (accessor-method qualifiers))))) t))
    (ccl::%clear-class-primary-slot-accessor-offsets
     (values (list (list (accessor-class-input :alist nil))
                   (list (accessor-class-input :alist '((:preserved . 19))))) t))
    (ccl::%non-standard-instance-slots
     (values (mapcar (lambda (x) (list (funcallable-input x))) '(nil 17 (1 . 2) :named)) t))
    ((ccl::%defgeneric-keys ccl::%set-defgeneric-keys)
     (values (mapcar (lambda (keys) (list (funcallable-input :key-owner) keys))
                    '(nil #() #(:first) #(:first :second))) t))
    (ccl::multi-method-index
     (values (loop for flags in '(nil (nil) (t) (nil t) (t nil) (t t) (nil nil t)) collect
               (list (vector (accessor-method nil)
                             (accessor-instance (find-class t) (list ccl::%class.name)) flags))) t))
    (ccl::non-dt-dcode-function
     (values (list (list (funcallable-input :found) t)
                   (list (funcallable-input :absent) nil)) t))
    (ccl::instance-slots
     (values (list (list (accessor-method '(:before)))
                   (list (accessor-class-input :alist '((:first . 17))))
                   (list (accessor-effective-slot :value 7))) t))
    (t (values nil nil))))
