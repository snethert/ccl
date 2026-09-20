(in-package :wasm32-compiler)
(defun compile-float-call-form (form name links &optional (safety 1))
 (unless (member safety '(0 1)) (refuse :float-safety))
 (let ((*b-float-service* t) (*b-float-safety* safety) (*b-integer-service* t) (*b-callable-metadata* t) (*b-allocation-retry* t))
  (compile-call-form form name links)))
(defun b-condition-runtime ()
 (let ((s (prior-float-b-condition-runtime)))
  (if *b-float-service*
   (numeric-text (numeric-text s "(i32.ne (local.get $n) (i32.const 15))" "(i32.and (i32.ne (local.get $n) (i32.const 15)) (i32.ne (local.get $n) (i32.const 19)))")
    "(i32.eq (local.get $mask) (i32.const 196636))" "(i32.ne (i32.and (local.get $mask) (i32.const 65536)) (i32.const 0))") s)))
(defun b-implicit-runtime ()
 (let ((s (prior-float-b-implicit-runtime)))
  (if *b-float-service*
   (numeric-text s "(else (i32.const 156))"
    "(else (if (result i32) (i32.eq (local.get $kind) (i32.const 35)) (then (i32.const 327708)) (else
     (if (result i32) (i32.eq (local.get $kind) (i32.const 36)) (then (i32.const 589852)) (else
     (if (result i32) (i32.eq (local.get $kind) (i32.const 37)) (then (i32.const 1114140)) (else
     (if (result i32) (i32.eq (local.get $kind) (i32.const 38)) (then (i32.const 2162716)) (else (i32.const 156))))))))))") s)))
(defun b-float-call (name forms)
 (let* ((names '(%float-add %float-sub %float-mul %float-div %float-lt %float-le %float-eq %float-ne %float-ge %float-gt %float-single %float-double))
        (op (position name names)) (operation (nth op '(+ - * / < <= = /= >= > float float))))
  (unless (= (length forms) 2) (refuse :float-arity))
  (b-frame 4 (lambda (root)
   (let ((a (b-wat "(i32.load offset=8 ~a)" root)) (b (b-wat "(i32.load offset=12 ~a)" root)) (status (temporary)))
    (let ((prefix (concatenate 'string
     (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a)" root (b-scalar (first forms)) root (b-scalar (second forms)))
     (with-output-to-string (s)
      (dolist (v (if (>= op 10) (list a) (list a b)))
       (write-string (b-wat "(if (i32.eqz (call $real_operand ~a)) (then ~a))" v (b-type-failure v (if (< op 4) 'number 'real))) s))))))
     (let ((floating (concatenate 'string
     (b-wat "(local.set ~a (call $float_slow (i32.const ~d) ~a (i32.const ~d)))" status op root *b-float-safety*)
     (b-wat "(if (i32.and (local.get ~a) (i32.const 31)) (then ~a))" status
      (b-frame 1 (lambda (pair)
       (b-wat "(i32.store offset=8 ~a ~a) (call $implicit_error_details ~a (local.get $top) ~a (i32.load offset=8 ~a)) unreachable"
        pair (b-cons (make-b-raw-code :text a) (make-b-raw-code :text (if (>= op 10) "(i32.const 77825)" (b-cons (make-b-raw-code :text b) (make-b-raw-code :text "(i32.const 77825)")))))
        (b-wat "(call $float_kind (i32.and (local.get ~a) (i32.const 31)))" status) (b-restart-symbol operation) pair))))
     (b-multiple (make-b-raw-code :text (b-wat "(i32.load offset=16 ~a)" root))))))
      (concatenate 'string prefix
       (if (< op 3)
        (b-wat "(if (i32.and (i32.eq (call $real_operand ~a) (i32.const 1)) (i32.eq (call $real_operand ~a) (i32.const 1))) (then ~a) (else ~a))"
         a b (b-integer-call (nth op '(%integer-add %integer-sub %integer-mul)) (list (make-b-raw-code :text a) (make-b-raw-code :text b))) floating)
        floating)))))))))
(defun b-float-runtime ()
 "(func $float_kind (param $flags i32) (result i32)
 (if (i32.eq (local.get $flags) (i32.const 1)) (then (return (i32.const 35))))
 (if (i32.eq (local.get $flags) (i32.const 2)) (then (return (i32.const 34))))
 (if (i32.eq (local.get $flags) (i32.const 4)) (then (return (i32.const 36))))
 (if (i32.eq (local.get $flags) (i32.const 8)) (then (return (i32.const 37))))
 (i32.const 38))
 (func $real_operand (param $x i32) (result i32) (local $p i32) (local $tag i32)
 (if (i32.eqz (i32.and (local.get $x) (i32.const 3))) (then (return (i32.const 1))))
 (if (i32.ne (i32.and (local.get $x) (i32.const 7)) (i32.const 6)) (then (return (i32.const 0))))
 (local.set $p (i32.sub (local.get $x) (i32.const 6))) (call $span (local.get $p) (i32.const 4))
 (local.set $tag (i32.and (i32.load (local.get $p)) (i32.const 255)))
 (if (i32.eq (local.get $tag) (i32.const 7)) (then (return (i32.const 1))))
 (if (i32.eq (i32.load (local.get $p)) (i32.const 271)) (then (call $span (local.get $p) (i32.const 8)) (return (i32.const 32))))
 (if (i32.eq (i32.load (local.get $p)) (i32.const 791)) (then (call $span (local.get $p) (i32.const 16)) (return (i32.const 64))))
 (if (i32.or (i32.eq (local.get $tag) (i32.const 10)) (i32.or (i32.eq (local.get $tag) (i32.const 26)) (i32.or (i32.eq (local.get $tag) (i32.const 71)) (i32.eq (local.get $tag) (i32.const 79))))) (then (throw $call_error (i32.const 32))))
 (i32.const 0))")
