(in-package :wasm32-compiler)
(defun numeric-text (text old new)
 (let ((p (search old text)))
  (unless (and p (not (search old text :start2 (+ p (length old))))) (error "Numeric runtime anchor"))
  (concatenate 'string (subseq text 0 p) new (subseq text (+ p (length old))))))
(defun b-condition-runtime ()
 (let ((s (prior-numeric-b-condition-runtime)))
  (if *b-integer-service*
   (numeric-text
    (numeric-text s "(i32.ne (local.get $n) (i32.const 13))" "(i32.and (i32.ne (local.get $n) (i32.const 13)) (i32.ne (local.get $n) (i32.const 15)))")
    "(i32.eq (local.get $mask) (i32.const 32796))"
    "(i32.or (i32.eq (local.get $mask) (i32.const 32796)) (i32.eq (local.get $mask) (i32.const 196636)))") s)))
(defun b-implicit-runtime ()
 (let ((s (prior-numeric-b-implicit-runtime)))
  (if *b-integer-service*
   (numeric-text s "(else (i32.const 156))" "(else (if (result i32) (i32.eq (local.get $kind) (i32.const 34)) (then (i32.const 196636)) (else (i32.const 156))))") s)))
(defun b-numeric-field (name forms)
 (unless (= (length forms) 1) (refuse :numeric-reader-arity))
 (b-frame 1 (lambda (root)
  (b-wat "(i32.store offset=8 ~a ~a) ~a" root (b-scalar (first forms))
   (b-multiple (make-b-raw-code :text (b-wat "(call $condition_field (i32.load offset=8 ~a) (i32.const 16384) (i32.const ~d) (local.get $top))" root (if (eq name '%numeric-operation) 8 12))))))))
(defun b-integer-call (name forms)
 (let ((op (position name '(%integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate))))
  (unless (= (length forms) (if (= op 4) 1 2)) (refuse :integer-arity))
  (b-frame 2 (lambda (root)
   (let ((a (b-wat "(i32.load offset=8 ~a)" root)) (b (b-wat "(i32.load offset=12 ~a)" root)))
    (concatenate 'string
     (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)" root (b-scalar (first forms)) root (if (= op 4) "(i32.const 0)" (b-scalar (second forms))))
     ;; Native CCL treats an explicit NIL divisor like the omitted default.
     ;; Evaluation is already complete; normalize only the private operand root.
     (when (= op 5) (b-wat "(if (i32.eq ~a (i32.const 77825)) (then (i32.store offset=12 ~a (i32.const 4))))" b root))
     (with-output-to-string (s)
      (dolist (value (cond ((= op 4) (list a)) ((= op 3) (list b a)) (t (list a b))))
       ;; Recognised noninteger numbers stay at the unsupported-numeric boundary;
       ;; they must not signal TYPE-ERROR with NUMBER as their expected type.
       (write-string (b-wat "(if (i32.eqz (call $integer_operand ~a)) (then ~a))" value (b-type-failure value (cond ((< op 3) 'number) ((= op 5) 'real) (t 'integer)))) s)))
     (when (= op 5)
      (b-wat "(if (i32.eqz ~a) (then ~a))" b
       (b-frame 1 (lambda (pair)
        (b-wat "(i32.store offset=8 ~a ~a) (call $implicit_error_details (i32.const 34) (local.get $top) ~a (i32.load offset=8 ~a)) unreachable"
         pair (b-cons (make-b-raw-code :text a) (make-b-raw-code :text (b-cons (make-b-raw-code :text b) (make-b-raw-code :text "(i32.const 77825)")))) (b-restart-symbol 'truncate) pair)))))
     (b-wat "(local.set $count (call $integer (i32.const ~d) ~a)) ~a
      (i32.store (local.get $results) (i32.load offset=8 ~a))
      (if (i32.eq (local.get $count) (i32.const 2)) (then (i32.store offset=4 (local.get $results) (i32.load offset=12 ~a))))"
      op root (b-ensure-results "(local.get $count)") root root)))))))
;; Keep the accepted arithmetic helper unchanged; add a checked classification
;; of admitted operands before entering it.
(setf (symbol-function 'prior-numeric-integer-runtime) (symbol-function 'b-integer-runtime))
(defun b-integer-runtime ()
 (concatenate 'string (prior-numeric-integer-runtime)
 "(func $integer_operand (param $x i32) (result i32) (local $p i32) (local $tag i32)
 (if (i32.eqz (i32.and (local.get $x) (i32.const 3))) (then (return (i32.const 1))))
 (if (i32.ne (i32.and (local.get $x) (i32.const 7)) (i32.const 6)) (then (return (i32.const 0))))
 (local.set $p (i32.sub (local.get $x) (i32.const 6))) (call $span (local.get $p) (i32.const 4))
 (local.set $tag (i32.and (i32.load (local.get $p)) (i32.const 255)))
 (if (i32.eq (local.get $tag) (i32.const 7)) (then (return (i32.const 1))))
 (if (i32.or (i32.or (i32.eq (local.get $tag) (i32.const 10)) (i32.eq (local.get $tag) (i32.const 26)))
  (i32.or (i32.or (i32.eq (local.get $tag) (i32.const 15)) (i32.eq (local.get $tag) (i32.const 23)))
   (i32.or (i32.eq (local.get $tag) (i32.const 71)) (i32.eq (local.get $tag) (i32.const 79)))))
  (then (throw $call_error (i32.const 32))))
 (i32.const 0))"))
