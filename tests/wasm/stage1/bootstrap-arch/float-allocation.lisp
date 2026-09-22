(defun bootstrap-allocate-float (forms)
  (let* ((count (ccl::acode-fixnum-form-p (first forms)))
         (subtag (ccl::acode-fixnum-form-p (second forms)))
         (bytes (cond ((and (eql count 1)
                           (eql subtag wasm32::subtag-single-float)) 8)
                      ((and (eql count 3)
                           (eql subtag wasm32::subtag-double-float)) 16))))
    (when (and bytes (= (length forms) 2))
      (b-wat "(i32.add ~a (i32.const 6))"
             (b-heap-block bytes
               (lambda (base)
                 (b-wat "(memory.fill ~a (i32.const 0) (i32.const ~d))
                          (i32.store ~a (i32.const ~d))"
                        base bytes base (+ (ash count 8) subtag))))))))

