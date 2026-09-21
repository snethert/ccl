(in-package :wasm32-compiler)

;;; The existing condition constructor owns the class layout and the existing
;;; dispatcher owns handler masking and transfers. Keep the new arguments in
;;; the caller's roots until the constructor has finished allocating.
(defun bootstrap-condition (mask values)
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (b-wat "(block (result i32) ~a)"
    (b-frame 2
      (lambda (root)
        (let ((object (temporary)))
          (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)
                  (local.set ~a ~a)
                  (i32.store offset=8 (call $condition_slots (local.get ~a)) (i32.load offset=8 ~a))
                  (i32.store offset=12 (call $condition_slots (local.get ~a)) (i32.load offset=12 ~a))
                  (local.get ~a)"
                 root (first values) root (second values) object
                 (if *b-allocation-retry*
                   (b-wat "(call $condition_new (i32.const ~d) (i32.add ~a (i32.const 8)))" mask root)
                   (b-wat "(call $condition_new (i32.const ~d) (i32.load offset=8 ~a) (i32.load offset=12 ~a))" mask root root))
                 object root object root object))))))

(defun bootstrap-immediate (form)
  (when (and (ccl::acode-p form)
             (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::immediate))
    (values (first (ccl::acode-operands form)) t)))

(defun bootstrap-signal (forms fatal)
  (unless forms (refuse :bootstrap-signal-arity))
  (multiple-value-bind (designator constant) (bootstrap-immediate (car forms))
    (let* ((class (and constant (symbolp designator) designator))
           (schema (assoc class '((simple-condition 36 :format-control :format-arguments)
                                  (simple-error 124 :format-control :format-arguments)
                                  (ccl::simple-program-error 2108 :format-control :format-arguments)
                                  (type-error 156 :datum :expected-type)
                                  (arithmetic-error 65564 :operation :operands)
                                  (division-by-zero 196636 :operation :operands))))
           (*b-tail-position* nil) (*b-producer-target* nil))
      (when (and class (not schema)) (refuse :bootstrap-condition-class))
      (when class
        (unless (evenp (length (cdr forms))) (refuse :bootstrap-condition-initargs))
        (loop for tail on (cdr forms) by #'cddr for key = (car tail) do
          (unless (member (bootstrap-immediate key) (cddr schema))
            (refuse :bootstrap-condition-initarg))))
      (b-frame (length forms)
        (lambda (root)
          (let ((values (loop for i below (length forms)
                             collect (b-wat "(i32.load offset=~d ~a)" (+ 8 (* i 4)) root))))
            (with-output-to-string (s)
              (loop for form in forms for i from 0 do
                (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* i 4)) root (b-scalar form)))
              (let* ((arguments
                       (if class
                         (loop for key in (cddr schema) collect
                           (or (loop for (k v) on (cdr forms) by #'cddr
                                     for i from 2 by 2
                                     when (eq (bootstrap-immediate k) key) return (nth i values))
                               (if (member key '(:format-control :datum :expected-type))
                                 "(i32.const 83)" "(i32.const 77825)")))
                         (list (car values)
                               (reduce (lambda (value tail)
                                         (b-cons (make-b-raw-code :text value)
                                                 (make-b-raw-code :text tail)))
                                       (cdr values) :from-end t :initial-value "(i32.const 77825)"))))
                     (condition
                       (if class
                         (bootstrap-condition (second schema) arguments)
                         (b-wat "(if (result i32) (i32.eq ~a (i32.const 764))
                                  (then ~a) (else ~a ~a))"
                                (bootstrap-typecode (car values))
                                (bootstrap-condition (if fatal 124 36) arguments)
                                (if (cdr forms) (b-condition "(i32.const 1)" 4) "")
                                (car values)))))
                (write-string (b-signal (make-b-raw-code :text condition) fatal) s)))))))))

(defun bootstrap-condition-reader (name forms)
  (unless (= (length forms) 1) (refuse :bootstrap-condition-reader-arity))
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (let* ((simple (member name '(simple-condition-format-control simple-condition-format-arguments)))
         (offset (if (member name '(simple-condition-format-control type-error-datum)) 8 12)))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((value (temporary)))
             (b-wat "(local.set ~a (call $condition_field ~a (i32.const ~d) (i32.const ~d) (local.get $top))) ~a (local.get ~a)"
                    value (car values) (if simple 8 32) offset
                    (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const 83))" value) 4)
                    value))))))))

(defun library-condition-call (name forms)
  (if (member name '(simple-condition-format-control simple-condition-format-arguments))
    (bootstrap-condition-reader name forms)
    (library-prior-call name forms)))

(defun bootstrap-character (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((x (car values)))
        (case op
          ((ccl::char-code ccl::%char-code)
           (b-wat "~a (i32.shl (i32.shr_u ~a (i32.const 8)) (i32.const 2))"
                  (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 255)) (i32.const 75))" x) 5) x))
          (t
           (b-wat "~a (if (result i32) (i32.and (i32.lt_u ~a (i32.const 4456448))
                      (i32.or (i32.lt_u ~a (i32.const 221184)) (i32.ge_u ~a (i32.const 229376))))
                    (then (i32.or (i32.shl ~a (i32.const 6)) (i32.const 75))) (else (i32.const 77825)))"
                  (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 4456448)))" x x) 5) x x x x)))))))

(defun bootstrap-string-access (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (object index &optional value) values
        (let* ((base (temporary)) (header (temporary))
               (address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) ~a))" base index)))
          (with-output-to-string (s)
            (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
            (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
            (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 191))" header) 4) s)
            (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
            (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.shl (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const 2))))" base header)
            (if value
              (progn
                (write-string
                 (b-condition
                  (if (eq op 'ccl::%set-scharcode)
                    (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 4456448)))" value value)
                    (b-wat "(i32.ne (i32.and ~a (i32.const 255)) (i32.const 75))" value)) 5) s)
                (format s "(i32.store ~a (i32.shr_u ~a (i32.const ~d))) ~a"
                        address value (if (eq op 'ccl::%set-scharcode) 2 8) value))
              (format s "(i32.or (i32.shl (i32.load ~a) (i32.const ~d)) (i32.const ~d))"
                      address (if (eq op 'ccl::%scharcode) 2 8)
                      (if (eq op 'ccl::%scharcode) 0 75)))))))))

(defun bootstrap-operator (ir)
  (when (ccl::acode-p ir)
    (let ((op (ccl::acode-operator-name (ccl::acode-operator ir)))
          (args (ccl::acode-operands ir)))
      (or (case op
            ((ccl::char-code ccl::%char-code ccl::code-char ccl::%code-char ccl::%valid-code-char)
             (bootstrap-character op args))
            ((ccl::%sbchar ccl::%scharcode ccl::%set-sbchar ccl::%set-scharcode)
             (bootstrap-string-access op args))
            (ccl::neq
             (bootstrap-operands (cdr args)
               (lambda (values)
                 (bootstrap-boolean (b-wat "(i32.eq ~a ~a)" (first values) (second values))
                                    (ccl::acode-immediate-operand (car args))))))
            (ccl::int>0-p
             (bootstrap-operands (cdr args)
               (lambda (values)
                 (b-wat "~a ~a"
                        (b-condition (b-wat "(i32.and ~a (i32.const 3))" (car values)) 5)
                        (bootstrap-boolean (b-wat "(i32.gt_s ~a (i32.const 0))" (car values))))))))
          (or (or (bootstrap-array-operator op args) (bootstrap-symbol-operator op args)) (library-prior-operator ir))))))

(defun bootstrap-symbol-pointer (form)
  (bootstrap-operands (list form)
    (lambda (values)
      (let ((x (car values)))
        (b-wat "(if (result i32) (i32.eq ~a (i32.const 77825))
                 (then (i32.const ~d))
                 (else ~a (drop (call $object_base ~a (i32.const 32) (i32.const 1850))) ~a))"
               x (+ wasm32::canonical-nil-value wasm32::nilsym-offset)
               (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" x) 5) x x)))))

(defun bootstrap-symbol-operator (op args)
  (case op
    (ccl::%unbound-marker "(i32.const 51)")
    (ccl::%symbol->symptr (bootstrap-symbol-pointer (car args)))
    ((ccl::%symptr->symvector ccl::%symvector->symptr) (b-scalar (car args)))))

(defun bootstrap-numeric-call (name forms)
  (case name
    ((ccl::%symptr-value ccl::%set-symptr-value)
     (unless (= (length forms) (if (eq name 'ccl::%symptr-value) 1 2))
       (refuse :bootstrap-symbol-arity))
     (b-multiple
      (make-b-raw-code :text
        (bootstrap-operands forms
          (lambda (values)
            (let ((location (b-wat "(call $special_location ~a)" (first values))))
              (if (eq name 'ccl::%symptr-value)
                (b-wat "(i32.load ~a)" location)
                (b-wat "(i32.store ~a ~a) ~a" location (second values) (second values)))))))))
    ((type-error-datum type-error-expected-type)
     (bootstrap-condition-reader name forms))
    (t (library-condition-call name forms))))

(defun bootstrap-array-operator (op args)
  (when (member op '(ccl::%typed-uvref ccl::%typed-uvset))
    (let ((kind (ccl::acode-immediate-operand (car args)))
          (storep (eq op 'ccl::%typed-uvset)))
      (unless (eq kind :unsigned-8-bit-vector) (refuse :bootstrap-array-kind))
      (bootstrap-operands (cdr args)
        (lambda (values)
          (let* ((object (first values)) (value (and storep (second values)))
                 (index (if storep (third values) (second values)))
                 (base (temporary)) (header (temporary))
                 (address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))" base index)))
            (with-output-to-string (s)
              (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
              (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
              (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 199))" header) 4) s)
              (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
              (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.shr_u (local.get ~a) (i32.const 8))))" base header)
              (if storep
                (progn
                  (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 1024)))" value value) 5) s)
                  (format s "(i32.store8 ~a (i32.shr_u ~a (i32.const 2))) ~a" address value value))
                (format s "(i32.shl (i32.load8_u ~a) (i32.const 2))" address)))))))))
