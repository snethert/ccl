(in-package :wasm32-compiler)

;;; An EQ backing vector must be valid before the next safepoint. Initialize
;;; the accepted strong-owner prefix and buckets inside one heap block.
(defun bootstrap-allocate-eq-vector (forms)
  (when (and *b-cpl-conditions*
             (eql (ccl::acode-fixnum-form-p (second forms)) wasm32::subtag-hash-vector))
    (unless (= (length forms) 2) (refuse :eq-vector-initial-element))
    (bootstrap-operands forms
      (lambda (values)
        (let ((count (first values)) (n (temporary)) (capacity (temporary)) (i (temporary)))
          (with-output-to-string (s)
            (write-string (b-condition
              (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.lt_s ~a (i32.const 88)) (i32.gt_u ~a (i32.const 131128))))" count count count) 6) s)
            (format s "(local.set ~a (i32.shr_u ~a (i32.const 2)))
                       (local.set ~a (i32.shr_u (i32.sub (local.get ~a) (i32.const 14)) (i32.const 1)))"
                    n count capacity n)
            (write-string (b-condition
              (b-wat "(i32.or (i32.and (local.get ~a) (i32.const 1))
                        (i32.and (local.get ~a) (i32.sub (local.get ~a) (i32.const 1))))"
                     n capacity capacity) 6) s)
            (write-string
              (b-wat "(i32.add ~a (i32.const 6))"
                (bootstrap-heap-block
                  (b-wat "(i32.add (i32.shl (local.get ~a) (i32.const 2)) (i32.const 8))" n)
                  (lambda (base bytes)
                    (with-output-to-string (out)
                      (format out "(memory.fill ~a (i32.const 0) ~a)
                                   (i32.store ~a (i32.or (i32.shl (local.get ~a) (i32.const 8)) (i32.const 74)))"
                              base bytes base n)
                      (loop for word in '(77825 1073741824 0 77825 77825 0 77825 0 0 -4 243 77825)
                            for offset from 4 by 4 do
                              (format out "(i32.store offset=~d ~a (i32.const ~d))" offset base word))
                      (format out "(i32.store offset=52 ~a (i32.shl (local.get ~a) (i32.const 2)))
                                   (local.set ~a (i32.const 0))
                                   (block $eq_done (loop $eq_fill
                                     (br_if $eq_done (i32.ge_u (local.get ~a) (local.get ~a)))
                                     (i32.store (i32.add ~a (i32.add (i32.const 60) (i32.shl (local.get ~a) (i32.const 3)))) (i32.const 243))
                                     (i32.store (i32.add ~a (i32.add (i32.const 64) (i32.shl (local.get ~a) (i32.const 3)))) (i32.const 77825))
                                     (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $eq_fill)))"
                              base capacity i i capacity base i base i i i))))) s)))))))
