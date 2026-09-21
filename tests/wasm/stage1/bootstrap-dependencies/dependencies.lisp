;;; Open-code target primitives and constant type tests. Native callers and
;;; their macro expansions remain unchanged. Dynamic type specifiers still
;;; call the full Lisp type system and remain real link dependencies.
(defparameter *bootstrap-type-predicates*
  '((null . null) (cons . consp) (list . listp) (atom . atom)
    (symbol . symbolp) (keyword . keywordp) (fixnum . ccl::fixnump)
    (bignum . ccl::bignump) (integer . integerp) (ratio . ccl::ratiop)
    (rational . rationalp) (real . realp) (number . numberp)
    (float . floatp) (short-float . ccl::short-float-p)
    (single-float . ccl::short-float-p) (double-float . ccl::double-float-p)
    (long-float . ccl::double-float-p) (complex . complexp)
    (character . characterp) (base-char . ccl::base-char-p)
    (string . stringp) (simple-string . ccl::simple-string-p)
    (simple-base-string . ccl::simple-base-string-p)
    (simple-vector . simple-vector-p) (simple-bit-vector . simple-bit-vector-p)
    (vector . vectorp) (array . arrayp) (sequence . ccl::sequencep)
    (function . functionp) (package . packagep)
    (ccl::istruct . ccl::istructp) (structure-object . ccl::structurep)))

(defun bootstrap-constant (value)
  (if (and (integerp value) (<= -536870912 value 536870911))
    (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) value)
    (ccl::make-acode (ccl::%nx1-operator ccl::immediate) value)))

(defun bootstrap-predicate-call (name forms)
  (bootstrap-primary
   (let ((*b-tail-position* nil) (*b-producer-target* nil))
     (b-call (bootstrap-constant name) (list forms nil)))))

(defun bootstrap-true-p (code)
  (b-wat "(i32.ne ~a (i32.const 77825))" code))

(defun bootstrap-small-literal-p (x)
  (or (null x) (eq x t) (and (integerp x) (<= -536870912 x 536870911))))

(defun bootstrap-type-supported-p (type)
  (cond ((symbolp type) (or (member type '(nil t bit signed-byte unsigned-byte))
                            (assoc type *bootstrap-type-predicates*)))
        ((consp type)
         (case (car type)
           ((or and) (every #'bootstrap-type-supported-p (cdr type)))
           (not (and (= (length type) 2) (bootstrap-type-supported-p (second type))))
           (eql (and (= (length type) 2) (bootstrap-small-literal-p (second type))))
           (member (every #'bootstrap-small-literal-p (cdr type)))
           (integer (and (<= (length type) 3)
                         (every (lambda (x) (or (eq x '*) (and (integerp x) (<= -536870912 x 536870911))
                                               (and (consp x) (null (cdr x)) (and (integerp (car x)) (<= -536870912 (car x) 536870911)))))
                                (cdr type))))
           ((signed-byte unsigned-byte)
            (and (= (length type) 2)
                 (or (eq (second type) '*)
                     (and (integerp (second type)) (<= 1 (second type) 28)))))
           (mod (and (= (length type) 2) (integerp (second type)) (<= 1 (second type) 536870911)))))))

(defun bootstrap-type-test (value type)
  (flet ((predicate (name)
           (bootstrap-true-p
            (bootstrap-predicate-call name (list (make-b-raw-code :text value))))))
    (cond ((null type) "(i32.const 0)")
          ((eq type t) "(i32.const 1)")
          ((eq type 'bit) (bootstrap-type-test value '(integer 0 1)))
          ((eq type 'signed-byte) (bootstrap-type-test value 'integer))
          ((eq type 'unsigned-byte) (bootstrap-type-test value '(integer 0 *)))
          ((assoc type *bootstrap-type-predicates*)
           (let ((name (cdr (assoc type *bootstrap-type-predicates*))))
             (case name
               (null (b-wat "(i32.eq ~a (i32.const 77825))" value))
               (t (predicate name)))))
          ((member (car type) '(or and))
           (reduce (lambda (part tail)
                     (if (eq (car type) 'or)
                       (b-wat "(if (result i32) ~a (then (i32.const 1)) (else ~a))"
                              (bootstrap-type-test value part) tail)
                       (b-wat "(if (result i32) ~a (then ~a) (else (i32.const 0)))"
                              (bootstrap-type-test value part) tail)))
                   (cdr type) :from-end t
                   :initial-value (if (eq (car type) 'or) "(i32.const 0)" "(i32.const 1)")))
          ((eq (car type) 'not) (b-wat "(i32.eqz ~a)" (bootstrap-type-test value (second type))))
          ((member (car type) '(eql member))
           (reduce (lambda (item tail)
                     (b-wat "(if (result i32) ~a (then (i32.const 1)) (else ~a))"
                            (bootstrap-true-p
                             (bootstrap-predicate-call 'eql
                               (list (make-b-raw-code :text value) (bootstrap-constant item)))) tail))
                   (cdr type) :from-end t :initial-value "(i32.const 0)"))
          ((eq (car type) 'mod) (bootstrap-type-test value `(integer 0 (,(second type)))))
          ((member (car type) '(signed-byte unsigned-byte))
           (let ((bits (second type)))
             (bootstrap-type-test value
               (if (eq bits '*)
                 (if (eq (car type) 'signed-byte) 'integer '(integer 0 *))
                 (if (eq (car type) 'signed-byte)
                   `(integer ,(- (ash 1 (1- bits))) (,(ash 1 (1- bits))))
                   `(integer 0 (,(ash 1 bits))))))))
          ((eq (car type) 'integer)
           (let ((test "(i32.const 1)"))
             (loop for bound in (cdr type) for lower = t then nil do
               (unless (eq bound '*)
                 (let* ((exclusive (consp bound)) (n (if exclusive (car bound) bound))
                        (op (if lower (if exclusive '> '>=) (if exclusive '< '<=))))
                   (setq test
                         (b-wat "(if (result i32) ~a (then ~a) (else (i32.const 0)))"
                                (bootstrap-true-p
                                 (bootstrap-primary
                                  (bootstrap-numeric-call op
                                    (list (make-b-raw-code :text value) (bootstrap-constant n))))) test)))))
             (b-wat "(if (result i32) ~a (then ~a) (else (i32.const 0)))"
                    (predicate 'integerp) test))))))

(defun bootstrap-type-call (name forms)
  (when (and (member (length forms) '(2 3))
             (or (= (length forms) 2)
                 (and (eq name 'typep)
                      (multiple-value-bind (env constant) (bootstrap-immediate (third forms))
                        (and constant (null env))))))
    (multiple-value-bind (type constant) (bootstrap-immediate (second forms))
      (when (and constant (bootstrap-type-supported-p type))
        (b-multiple
         (make-b-raw-code :text
           (bootstrap-operands forms
             (lambda (values)
               (let ((object (first values)) (test (bootstrap-type-test (first values) type)))
                 (if (eq name 'typep)
                   (bootstrap-boolean test)
                   (b-wat "(if (i32.eqz ~a) (then
                             (call $implicit_error_details (i32.const 5) (local.get $top) ~a ~a) unreachable)) ~a"
                          test object (second values) object)))))))))))

(defun bootstrap-assq (forms)
  (when (= (length forms) 2)
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((cursor (temporary)) (pair (temporary)) (exit (temporary)))
             (b-wat "(local.set ~a ~a)
                     (block ~a (result i32) (loop
                       (if (i32.eq (local.get ~a) (i32.const 77825)) (then (br ~a (i32.const 77825))))
                       (local.set ~a ~a)
                       (if (i32.ne (local.get ~a) (i32.const 77825)) (then
                         (if (i32.eq ~a ~a) (then (br ~a (local.get ~a))))))
                       (local.set ~a ~a) (br 0)) unreachable)"
                    cursor (second values) exit cursor exit pair
                    (bootstrap-primary (b-checked-cons-operation 'car (list (make-b-raw-code :text (b-local cursor)))))
                    pair (first values)
                    (bootstrap-primary (b-checked-cons-operation 'car (list (make-b-raw-code :text (b-local pair)))))
                    exit pair cursor
                    (bootstrap-primary (b-checked-cons-operation 'cdr (list (make-b-raw-code :text (b-local cursor)))))))))))))

(defun bootstrap-logical-call (name forms)
  (b-multiple
   (make-b-raw-code :text
     (bootstrap-operands forms
       (lambda (values)
         (with-output-to-string (s)
           (dolist (value values)
             (write-string
              (b-wat "(if (i32.and ~a (i32.const 3)) (then
                        (if (i32.eq ~a (i32.const 28)) (then (throw $call_error (i32.const 32)))) ~a))"
                     value (bootstrap-typecode value) (b-type-failure value 'integer)) s))
           (write-string
            (reduce (lambda (a b) (b-wat "(i32.~a ~a ~a)" (if (eq name 'logand) "and" "or") a b))
                    values :initial-value (if (eq name 'logand) "(i32.const -4)" "(i32.const 0)")) s)))))))

(defun bootstrap-subtract (forms)
  (when forms
    (b-frame (length forms)
      (lambda (root)
        (with-output-to-string (s)
          (loop for form in forms for i from 0 do
            (format s "(i32.store offset=~d ~a ~a)" (+ 8 (* 4 i)) root (b-scalar form)))
          (let ((a (make-b-raw-code :text (b-wat "(i32.load offset=8 ~a)" root))))
            (if (null (cdr forms))
              (write-string (b-float-call '%float-mul (list a (bootstrap-constant -1))) s)
              (loop for i from 1 below (length forms) do
                (write-string
                 (b-float-call '%float-sub
                   (list a (make-b-raw-code :text (b-wat "(i32.load offset=~d ~a)" (+ 8 (* 4 i)) root)))) s)
                (format s "(i32.store offset=8 ~a (i32.load (local.get $results)))" root)))))))))

(defun bootstrap-error-call (forms)
  ;; An improper list is outside this packet's proper-sequence domain.
  (when (and (= (length forms) 2)
             (ccl::acode-p (first forms))
             (member (ccl::acode-operator-name (ccl::acode-operator (first forms)))
                     '(ccl::fixnum ccl::immediate))
             (eql (first (ccl::acode-operands (first forms))) ccl::$ximproperlist))
    (return-from bootstrap-error-call
      (b-multiple (make-b-raw-code :text
        (bootstrap-operands (cdr forms)
          (lambda (values) (declare (ignore values))
            "(throw $call_error (i32.const 45)) unreachable"))))))
  (when (= (length forms) 3)
    (let* ((code (first forms)) (op (and (ccl::acode-p code) (ccl::acode-operator-name (ccl::acode-operator code))))
           (n (and (member op '(ccl::fixnum ccl::immediate)) (first (ccl::acode-operands code)))))
      (when (eql n ccl::$xwrongtype)
        (b-frame 2
          (lambda (root)
            (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)
                    (i32.store offset=12 ~a ~a)
                    (call $implicit_error_details (i32.const 5) (local.get $top)
                          (i32.load offset=8 ~a) (i32.load offset=12 ~a)) unreachable"
                   root (b-scalar (second forms)) root (b-scalar (third forms)) root
                   (bootstrap-predicate-call 'ccl::%type-error-type
                     (list (make-b-raw-code :text (b-wat "(i32.load offset=12 ~a)" root))))
                   root root)))))))

(defun bootstrap-ldb (forms)
  (when (= (length forms) 2)
    (let* ((form (first forms))
           (op (and (ccl::acode-p form) (ccl::acode-operator-name (ccl::acode-operator form))))
           (spec (and (member op '(ccl::fixnum ccl::immediate)) (first (ccl::acode-operands form)))))
      (when (and (integerp spec) (<= 0 spec))
        (let ((size (byte-size spec)) (position (byte-position spec)))
          (when (<= size 29)
            (b-multiple
             (make-b-raw-code :text
               (bootstrap-operands forms
                 (lambda (values)
                   (let ((x (second values)))
                     (b-wat "(if (i32.and ~a (i32.const 3)) (then
                               (throw $call_error (i32.const 32))))
                             (i32.shl (i32.and (i32.shr_s (i32.shr_s ~a (i32.const 2))
                                                       (i32.const ~d)) (i32.const ~d)) (i32.const 2))"
                            x x (min position 31) (1- (ash 1 size))))))))))))))

(defun bootstrap-dependency-call (name forms)
  (case name
    (ldb (bootstrap-ldb forms))
    (ccl::assq (bootstrap-assq forms))
    ((logand logior) (bootstrap-logical-call name forms))
    (- (bootstrap-subtract forms))
    ((typep ccl::require-type) (bootstrap-type-call name forms))
    ((ccl::%err-disp) (bootstrap-error-call forms))
))

(defun bootstrap-dependency-operator (ir)
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir)))
        (args (ccl::acode-operands ir)))
    (case op
      ((ccl::logand2 ccl::logior2)
       (bootstrap-primary (bootstrap-logical-call (if (eq op 'ccl::logand2) 'logand 'logior) args)))
      (ccl::%err-disp
       (let ((code (bootstrap-error-call (first (first args)))))
         (when code (bootstrap-primary code)))))))
