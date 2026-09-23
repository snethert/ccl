    ;; LAP-primitive witnesses (w32-lap.lisp).  Where the 64-bit native
    ;; entry has a different contract, the native side computes the
    ;; reference in ordinary arithmetic.
    (defun core-lap-string-hash (s)
      #+wasm32-target (ccl::%pname-hash s (length s))
      #-wasm32-target
      (let ((accum 0))
        (dotimes (i (length s) (logand accum #x07ffffff))
          (setq accum (logxor (logand #xffffffff
                                      (logior (ash accum 5) (ash accum -27)))
                              (char-code (schar s i)))))))
    (defun core-lap-substring-hash (s start len)
      #+wasm32-target (ccl::%string-hash start s len)
      #-wasm32-target
      (let ((accum 0))
        (dotimes (i len (logand accum #x07ffffff))
          (setq accum (logxor (logand #xffffffff
                                      (logior (ash accum 5) (ash accum -27)))
                              (char-code (schar s (+ start i))))))))
    (defun core-lap-store-conditional (v i old new)
      (values (ccl::%store-node-conditional
               (+ target::misc-data-offset (* i target::node-size)) v old new)
              v))
    (defun core-lap-atomic-incf (v i by)
      (values (ccl::%atomic-incf-node
               by v (+ target::misc-data-offset (* i target::node-size)))
              v))
    (defun core-lap-gvector-overlap (n direction)
      (let ((v (vector 0 1 2 3 4 5 6 7 8 9)))
        (core-collect)
        (if direction
          (ccl::%copy-gvector-to-gvector v 0 v 2 n)
          (ccl::%copy-gvector-to-gvector v 2 v 0 n))
        v))
    (defun core-lap-header-offset (offset)
      (let* ((base (make-array 10))
             (displaced (make-array 4 :displaced-to base
                                      :displaced-index-offset offset)))
        (multiple-value-bind (data data-offset)
            (ccl::%array-header-data-and-offset displaced)
          (values (eq data base) data-offset))))
    (defun core-lap-make-short (significand biased-exp sign)
      #+wasm32-target
      (ccl::%make-short-float-from-fixnums (ccl::%make-sfloat)
                                          significand biased-exp sign)
      #-wasm32-target
      (ccl::make-short-float-from-fixnums significand biased-exp sign))
    ;; The native entry returns the allocation pointer as a second value.
    (defun core-lap-allocate-list (x n) (values (ccl::%allocate-list x n)))
    (defun core-lap-sqrt-single (x)
      #+wasm32-target (ccl::%single-float-sqrt! x (ccl::%make-sfloat))
      #-wasm32-target (ccl::%single-float-sqrt x))
    (defun core-lap-sqrt-invalid (x)
      (handler-case (if (typep x 'double-float)
                      (ccl::%double-float-sqrt! x (ccl::%make-dfloat))
                      #+wasm32-target (ccl::%single-float-sqrt! x (ccl::%make-sfloat))
                      #-wasm32-target (ccl::%single-float-sqrt x))
        (floating-point-invalid-operation () :invalid)))
    (defun core-lap-hash-key-conditional (v i old new)
      (values (ccl::%set-hash-table-vector-key-conditional
               (+ target::misc-data-offset (* i target::node-size)) v old new)
              v))
    ;; Fixnums pass through; other objects give address bits, which differ
    ;; between hosts, so only the class of the answer is compared.
    (defun core-lap-strip-tag (x)
      (let ((r (ccl::strip-tag-to-fixnum x)))
        (if (ccl:fixnump x) r (and (ccl:fixnump r) (not (eq r x))))))
    ;; NIL's symbol pointer is not NIL; the round trip must give NIL back.
    (defun core-lap-symptr-round-trip (s)
      #+wasm32-target (ccl::%symptr->symbol (ccl::%symbol->symptr s))
      #-wasm32-target s)
    ;; The harness calls every case for multiple values.
    (defun core-lap-called-for-mv (x) (values (ccl::called-for-mv-p) x)
)
