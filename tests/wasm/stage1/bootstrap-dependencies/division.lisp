(defun bootstrap-integer-division (root)
  ;; B-FLOAT-CALL has evaluated, rooted and checked both operands as integers.
  ;; The integer capability requires a two-slot frame at the root-chain head.
  (b-frame 2
    (lambda (operands)
      (let ((a (b-wat "(i32.load offset=8 ~a)" operands))
            (b (b-wat "(i32.load offset=12 ~a)" operands)))
        (concatenate
         'string
         (b-wat "(i32.store offset=8 ~a (i32.load offset=8 ~a))
                 (i32.store offset=12 ~a (i32.load offset=12 ~a))"
                operands root operands root)
         (b-wat "(if (i32.eqz ~a) (then ~a))" b
           (b-frame 1
             (lambda (pair)
               (b-wat "(i32.store offset=8 ~a ~a)
                       (call $implicit_error_details (i32.const 34) (local.get $top)
                             ~a (i32.load offset=8 ~a)) unreachable"
                      pair
                      (b-cons (make-b-raw-code :text a)
                              (make-b-raw-code :text
                                (b-cons (make-b-raw-code :text b)
                                        (make-b-raw-code :text "(i32.const 77825)"))))
                      (b-restart-symbol '/) pair))))
         (b-wat "(drop (call $integer (i32.const 5) ~a))" operands)
         ;; A ratio result remains outside this subset. Never return truncation.
         (b-condition (b-wat "(i32.ne ~a (i32.const 0))" b) 45)
         (b-multiple (make-b-raw-code :text a)))))))

(defun bootstrap-handler-mask (value)
  ;; Native HANDLER-BIND expansions retain their quoted class symbols.
  ;; Compare symbol identities; their addresses are not condition bitmasks.
  (let ((x (temporary)))
    (with-output-to-string (s)
      (format s "(block (result i32) (local.set ~a ~a)" x value)
      (format s "(if (i32.eqz (i32.and (local.get ~a) (i32.const 3))) (then (br 1 (i32.shr_u (local.get ~a) (i32.const 2)))))" x x)
      (dolist (name '(condition serious-condition error simple-condition simple-error
                     type-error control-error warning simple-warning program-error
                     undefined-function unbound-variable storage-condition
                     ccl::no-applicable-method-exists arithmetic-error division-by-zero
                     floating-point-invalid-operation floating-point-overflow
                     floating-point-underflow floating-point-inexact))
        (format s "(if (i32.eq (local.get ~a) ~a) (then (br 1 (i32.const ~d))))"
                x (b-restart-symbol name) (b-condition-mask name)))
      (write-string "(throw $call_error (i32.const 12)))" s))))
