(in-package :wasm32-compiler)

(defun bootstrap-boolean (test &optional (condition :eq))
  (unless (member condition '(:eq :ne)) (refuse :bootstrap-condition))
  (b-wat "(if (result i32) ~a (then (i32.const ~d)) (else (i32.const ~d)))"
         test (if (eq condition :eq) 77838 77825)
         (if (eq condition :eq) 77825 77838)))

(defun bootstrap-operands (forms function)
  ;; Every operand remains rooted while later operands run.
  (b-wat "(block (result i32) ~a)"
         (b-frame (length forms)
                  (lambda (base)
                    (with-output-to-string (s)
                      (loop for form in forms for i from 0 do
                        (format s "(i32.store offset=~d ~a ~a)"
                                (+ 8 (* 4 i)) base (b-scalar form)))
                      (write-string
                       (funcall function
                                (loop for i below (length forms)
                                      collect (b-wat "(i32.load offset=~d ~a)"
                                                     (+ 8 (* 4 i)) base)))
                       s))))))

(defun bootstrap-typecode (value)
  (let ((x (temporary)))
    (b-wat "(block (result i32) (local.set ~a ~a) (if (result i32) (i32.eq (i32.and (local.get ~a) (i32.const 3)) (i32.const 2)) (then (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4)) (i32.shl (i32.load8_u (i32.sub (local.get ~a) (i32.const 6))) (i32.const 2))) (else (i32.shl (i32.and (local.get ~a) (i32.const 3)) (i32.const 2)))))"
           x value x x x x)))

(defun bootstrap-node-access (op args)
  (bootstrap-operands
   args
   (lambda (values)
     (destructuring-bind (object index &optional value) values
       (let* ((base (temporary)) (header (temporary)) (answer (temporary))
              (subtag (case op
                        ((ccl::svref ccl::svset) wasm32::subtag-simple-vector)
                        ((ccl::struct-ref ccl::struct-set) wasm32::subtag-struct)))
              (address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) ~a))" base index)))
         (with-output-to-string (s)
           (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
           (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
           (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 2))" header) 4) s)
           (when subtag
             (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const ~d))" header subtag) 4) s))
           (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
           (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.shl (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const 2))))" base header)
           (if value
             (format s "(i32.store ~a ~a) ~a" address value value)
             (progn
               (format s "(local.set ~a (i32.load ~a))" answer address)
               (when (eq op 'ccl::%slot-ref)
                 (write-string (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const ~d))" answer wasm32::subtag-slot-unbound) 4) s))
               (format s "(local.get ~a)" answer)))))))))

(defun bootstrap-gvector (forms)
  (unless forms (refuse :bootstrap-gvector))
  (let ((subtag (ccl::acode-fixnum-form-p (car forms)))
        (n (length (cdr forms))))
    (unless (and subtag (<= 0 subtag 255)
                 (= (logand subtag 7) wasm32::fulltag-nodeheader))
      (refuse :bootstrap-gvector-subtag))
    (bootstrap-operands
     (cdr forms)
     (lambda (values)
       (b-wat "(i32.add ~a (i32.const 6))"
              (b-heap-block (* 8 (ceiling (1+ n) 2))
                            (lambda (base)
                              (with-output-to-string (s)
                                (format s "(i32.store ~a (i32.const ~d))" base (+ subtag (* 256 n)))
                                (loop for value in values for i from 1 do
                                  (format s "(i32.store offset=~d ~a ~a)" (* 4 i) base value))
                                (when (evenp n)
                                  (format s "(i32.store offset=~d ~a (i32.const 77825))" (* 4 (1+ n)) base))))))))))

(defun bootstrap-fixnum-operator (op forms &optional condition)
  (bootstrap-operands
   forms
   (lambda (values)
     (let ((a (first values)) (b (second values)))
       (with-output-to-string (s)
         (dolist (x values)
           (write-string (b-condition (b-wat "(i32.and ~a (i32.const 3))" x) 5) s))
         (write-string
          (case op
            (ccl::%i<>
             (bootstrap-boolean
              (b-wat "(i32.~a ~a ~a)"
                     (ecase condition (:eq "eq") (:ne "ne") (:lt "lt_s")
                            (:le "le_s") (:gt "gt_s") (:ge "ge_s")) a b)))
            ((ccl::%i+ ccl::fixnum-add-no-overflow)
             (b-wat "(i32.add ~a ~a)" a b))
            ((ccl::%i- ccl::fixnum-sub-no-overflow)
             (b-wat "(i32.sub ~a ~a)" a b))
            (ccl::%ilogand2 (b-wat "(i32.and ~a ~a)" a b))
            (ccl::%ilogior2 (b-wat "(i32.or ~a ~a)" a b))
            (ccl::%ilogxor2 (b-wat "(i32.xor ~a ~a)" a b))
            (ccl::%ilognot (b-wat "(i32.xor ~a (i32.const -4))" a))
            (t (refuse op)))
          s))))))

(defun bootstrap-operator (ir)
  (let ((op (ccl::acode-operator-name (ccl::acode-operator ir)))
        (args (ccl::acode-operands ir)))
    (case op
      ((ccl::lisptag ccl::fulltag)
       (b-wat "(i32.shl (i32.and ~a (i32.const ~d)) (i32.const 2))"
              (b-scalar (first args)) (if (eq op 'ccl::lisptag) 3 7)))
      (ccl::typecode (bootstrap-typecode (b-scalar (first args))))
      ((ccl::%err-disp ccl::%badarg2 ccl::%debug-trap)
       ;; These entries remain calls to CCL's own error/debugger machinery.
       ;; They are dependencies, never counted as installed primitives.
       (let ((name (case op (ccl::%badarg2 'ccl::%badarg)
                           (ccl::%debug-trap 'ccl::dbg) (t 'ccl::%err-disp))))
         (b-wat "(block (result i32) ~a (i32.load (local.get $results)))"
                (let ((*b-tail-position* nil))
                  (b-call (ccl::make-acode (ccl::%nx1-operator ccl::immediate) name)
                          (if (eq op 'ccl::%err-disp) (car args) (list args nil)))))))
      ((ccl::free-reference ccl::global-ref)
       (b-wat "(call $special_read_lisp ~a (local.get $top))"
              (b-special-symbol (first args))))
      (ccl::uvsize
       (let ((x (temporary)))
         (b-wat "(block (result i32) (local.set ~a ~a) ~a (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4)) (i32.shl (i32.shr_u (i32.load (i32.sub (local.get ~a) (i32.const 6))) (i32.const 8)) (i32.const 2)))"
                x (b-scalar (car args))
                (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6))" x) 4) x x)))
      (ccl::%lisp-word-ref
       (bootstrap-operands
        args
        (lambda (values)
          (destructuring-bind (base offset) values
            (b-wat "~a (i32.load (i32.add ~a ~a))"
                   (b-condition
                    (b-wat "(i64.gt_u (i64.add (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_u ~a)) (i64.const 4)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" base offset) 4)
                   base offset)))))
      (ccl::istruct-typep
       (bootstrap-operands
        (cdr args)
        (lambda (values)
          (let* ((object (first values)) (cell (second values))
                 (zero (ccl::make-acode (ccl::%nx1-operator ccl::fixnum) 0)))
            (bootstrap-boolean
             (b-wat "(if (result i32) (i32.eq ~a (i32.const ~d)) (then (i32.eq ~a ~a)) (else (i32.const 0)))"
                    (bootstrap-typecode object) (* 4 wasm32::subtag-istruct)
                    (bootstrap-node-access 'ccl::%svref (list (make-b-raw-code :text object) zero)) cell)
             (ccl::acode-immediate-operand (car args)))))))
      ((ccl::consp ccl::characterp ccl::base-char-p ccl::endp)
       (let ((x (temporary)) (cc (ccl::acode-immediate-operand (first args))))
         (b-wat "(block (result i32) (local.set ~a ~a) ~a ~a)"
                x (b-scalar (second args))
                (if (eq op 'ccl::endp)
                  (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 1))" x) 5) "")
                (bootstrap-boolean
                 (case op
                   (ccl::consp (b-wat "(i32.and (i32.ne (local.get ~a) (i32.const 77825)) (i32.eq (i32.and (local.get ~a) (i32.const 7)) (i32.const 1)))" x x))
                   (ccl::endp (b-wat "(i32.eq (local.get ~a) (i32.const 77825))" x))
                   (t (b-wat "(i32.eq (i32.and (local.get ~a) (i32.const 255)) (i32.const 75))" x))) cc))))
      ((ccl::%svref ccl::svref ccl::struct-ref ccl::%slot-ref
        ccl::%svset ccl::svset ccl::struct-set)
       (bootstrap-node-access op args))
      (ccl::%gvector
       (unless (null (second (first args))) (refuse :bootstrap-gvector-spread))
       (bootstrap-gvector (first (first args))))
      ((ccl::ivector-typecode-p ccl::gvector-typecode-p)
       (let ((x (temporary)))
         (b-wat "(block (result i32) (local.set ~a ~a) (if (result i32) (i32.eq (i32.and (local.get ~a) (i32.const 31)) (i32.const ~d)) (then (local.get ~a)) (else (i32.const 0))))"
                x (b-scalar (car args)) x
                (* 4 (if (eq op 'ccl::ivector-typecode-p) 7 2)) x)))
      (ccl::%ilogbitp
       (bootstrap-operands
        (cdr args)
        (lambda (values)
          (destructuring-bind (index value) values
            (b-wat "~a ~a ~a"
                   (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 120)))" index index) 5)
                   (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 5)
                   (bootstrap-boolean
                    (b-wat "(i32.eqz (i32.and (i32.shr_s ~a (i32.add (i32.shr_u ~a (i32.const 2)) (i32.const 2))) (i32.const 1)))" value index)
                    (ccl::acode-immediate-operand (car args))))))))
      (ccl::ash
       (b-wat "(block (result i32) ~a (i32.load (local.get $results)))"
              (b-integer-call '%integer-ash args)))
      (ccl::%i<> (bootstrap-fixnum-operator op (cdr args) (ccl::acode-immediate-operand (car args))))
      ((ccl::%i+ ccl::%i- ccl::fixnum-add-no-overflow ccl::fixnum-sub-no-overflow
        ccl::%ilogand2 ccl::%ilogior2 ccl::%ilogxor2 ccl::%ilognot)
       (bootstrap-fixnum-operator op args)))))

(defun bootstrap-numeric-call (name forms)
  (let ((entry (assoc name '((+ . %float-add) (- . %float-sub) (* . %float-mul)
                             (/ . %float-div) (< . %float-lt) (<= . %float-le)
                             (= . %float-eq) (/= . %float-ne) (>= . %float-ge)
                             (> . %float-gt)))))
    (cond ((and (member name '(functionp ccl::lfunp)) (= (length forms) 1))
           (b-multiple (make-b-raw-code :text
             (bootstrap-boolean
              (b-wat "(i32.eq ~a (i32.const 168))"
                     (bootstrap-typecode (b-scalar (car forms))))))))
          ((and (member name '(< <= = /= >= >)) (= (length forms) 2))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-operands
               forms
               (lambda (values)
                 (destructuring-bind (a b) values
                   (b-wat "(if (result i32) (i32.eqz (i32.and (i32.or ~a ~a) (i32.const 3))) (then ~a) (else (block (result i32) ~a (i32.load (local.get $results)))))"
                          a b
                          (bootstrap-boolean
                           (b-wat "(i32.~a ~a ~a)"
                                  (ecase name (< "lt_s") (<= "le_s") (= "eq")
                                         (/= "ne") (>= "ge_s") (> "gt_s")) a b))
                          (b-float-call (cdr entry)
                                        (list (make-b-raw-code :text a)
                                              (make-b-raw-code :text b))))))))))
          ((and entry (= (length forms) 2))
           (b-float-call (cdr entry) forms))
          ((and (eq name 'ash) (= (length forms) 2))
           (b-integer-call '%integer-ash forms))
          ((and (eq name 'integer-length) (= (length forms) 1))
           (b-integer-call '%integer-length forms))
          ((and (member name '(logand logior logxor)) (= (length forms) 2)
                (every (lambda (form) (ccl::acode-form-typep form 'fixnum t)) forms))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-fixnum-operator
               (ecase name (logand 'ccl::%ilogand2) (logior 'ccl::%ilogior2)
                      (logxor 'ccl::%ilogxor2)) forms)))))))

(defun bootstrap-emitted-operators ()
  (let ((counts nil))
    (maphash (lambda (ir emitted)
               (declare (ignore emitted))
               (let* ((name (ccl::acode-operator-name (ccl::acode-operator ir)))
                      (entry (assoc name counts)))
                 (if entry (incf (cdr entry)) (push (cons name 1) counts))))
             *bootstrap-emitted*)
    (sort counts #'string< :key (lambda (entry) (symbol-name (car entry))))))
