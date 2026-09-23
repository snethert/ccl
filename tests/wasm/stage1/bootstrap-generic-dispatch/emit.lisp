(in-package :wasm32-compiler)

;;; Match the logical argument and method bits computed by native pass 2.
;;; The bootstrap pool prefix is versioned by its magic word. Unlike native
;;; instruction immediates it remains a traced, portable part of the function.
(defun bootstrap-next-method-args-p (afunc)
  (let ((seen (make-hash-table :test #'eq)))
    (labels ((visit (form)
               (cond ((gethash form seen) nil)
                     ((typep form 'ccl::afunc)
                      (setf (gethash form seen) t)
                      (visit (ccl::afunc-acode form)))
                     ((ccl::acode-p form)
                      (setf (gethash form seen) t)
                      (let ((op (ccl::acode-operator-name (ccl::acode-operator form)))
                            (args (ccl::acode-operands form)))
                        (or (and (eq op 'ccl::%function)
                                 (eq (car args) 'ccl::%call-next-method-with-args))
                            (and (eq op 'ccl::call)
                                 (eq (bootstrap-immediate (car args))
                                     'ccl::%call-next-method-with-args))
                            (some #'visit args))))
                     ((consp form) (or (visit (car form)) (visit (cdr form)))))))
      (visit afunc))))

(defun bootstrap-lfun-bits (afunc)
  (let* ((args (ccl::acode-operands (ccl::afunc-acode afunc)))
         (methodp (logbitp ccl::$fbitmethodp (ccl::afunc-bits afunc)))
         (keys (fourth args))
         (bits (dpb (min 63 (- (length (first args)) (if methodp 1 0))) ccl::$lfbits-numreq 0)))
    (setq bits (dpb (min 31 (length (first (second args)))) ccl::$lfbits-numopt bits))
    (setq bits (dpb (min 63 (length (ccl::afunc-inherited-vars afunc))) ccl::$lfbits-numinh bits))
    (when (or (some (lambda (value) (not (ccl::nx-null value))) (second (second args)))
              (some #'identity (third (second args))))
      (setq bits (logior bits (ash 1 ccl::$lfbits-optinit-bit))))
    (when (third args)
      (setq bits (logior bits (ash 1 (if (consp (third args)) ccl::$lfbits-restv-bit ccl::$lfbits-rest-bit)))))
    (when keys (setq bits (logior bits (ash 1 ccl::$lfbits-keys-bit))))
    (when (first keys) (setq bits (logior bits (ash 1 ccl::$lfbits-aok-bit))))
    (when methodp
      (setq bits (logior bits (ash 1 ccl::$lfbits-method-bit)))
      (when (logbitp ccl::$fbitnextmethp (ccl::afunc-bits afunc))
        (setq bits (logior bits (ash 1 ccl::$lfbits-nextmeth-bit))))
      (when (or (logbitp ccl::$fbitnextmethargsp (ccl::afunc-bits afunc))
                (bootstrap-next-method-args-p afunc))
        (setq bits (logior bits (ash 1 ccl::$lfbits-nextmeth-with-args-bit)))))
    bits))

(defun bootstrap-function-info (value index)
  (let ((function (temporary)) (pool (temporary)) (offset (temporary)))
    (b-wat "(block (result i32)
      (local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))
      (local.set ~a (i32.load offset=24 (local.get ~a)))
      ~a
      (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4))
      ~a
      (local.set ~a (if (result i32) (i32.eq (i32.load offset=16 (local.get ~a)) (i32.const 77825))
                         (then (i32.const 0)) (else (i32.const 8))))
      ~a
      (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.add (local.get ~a) (i32.const 16)))
      ~a
      (i32.load offset=~d (i32.add (local.get ~a) (local.get ~a))))"
      function value pool function
      (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6))" pool) 4)
      pool
      (b-condition (b-wat "(i32.ne (i32.load8_u (i32.sub (local.get ~a) (i32.const 6))) (i32.const 250))" pool) 4)
      offset function
      (b-condition (b-wat "(i32.lt_u (i32.shr_u (i32.load (i32.sub (local.get ~a) (i32.const 6))) (i32.const 8)) (i32.add (i32.shr_u (local.get ~a) (i32.const 2)) (i32.const 3)))" pool offset) 4)
      pool offset
      (b-condition (b-wat "(i32.ne (i32.load (i32.add (local.get ~a) (i32.sub (local.get ~a) (i32.const 2)))) (i32.const ~d))" pool offset (* 4 #x574153)) 4)
      (- (* 4 index) 2) pool offset)))

(defun bootstrap-function-bits (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((function (temporary)))
        (b-wat "(block (result i32)
          (local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))
          (if (result i32) (i32.eq (i32.load (local.get ~a)) (i32.const 1834))
            (then (i32.load offset=28
                    (call $object_base (i32.load offset=28 (local.get ~a))
                      (i32.const 32) (i32.const 2042))))
            (else ~a)))"
          function (first values) function function
          (bootstrap-function-info (first values) 1))))))

(defun bootstrap-set-function-bits (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((side (temporary)) (function (first values)) (bits (second values)))
        (b-wat "(block (result i32)
          (local.set ~a (call $object_base
            (i32.load offset=28 (call $object_base ~a (i32.const 32) (i32.const 1834)))
            (i32.const 32) (i32.const 2042)))
          ~a
          (i32.store offset=28 (local.get ~a) ~a) ~a)"
          side function
          (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" bits bits) 4)
          side bits bits)))))

(defun bootstrap-function-keyvect (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((value (first values)) (function (temporary)) (keys (temporary)))
        (b-wat "(block (result i32)
          (local.set ~a (call $object_base ~a (i32.const 32) (i32.const 1578)))
          (if (result i32) (i32.eq (i32.load (local.get ~a)) (i32.const 1834))
            (then (i32.const 77825))
            (else
          (if (result i32) (i32.eq (i32.load offset=16 (local.get ~a)) (i32.const 77825))
            (then
              (local.set ~a ~a)
              (if (i32.ne (local.get ~a) (i32.const 77825))
                (then
                  (call $span (i32.sub (local.get ~a) (i32.const 6)) (i32.const 4))
                  ~a
                  (call $span (i32.sub (local.get ~a) (i32.const 6))
                    (i32.add (i32.const 4) (i32.shl (i32.shr_u
                      (i32.load (i32.sub (local.get ~a) (i32.const 6))) (i32.const 8)) (i32.const 2))))))
              (local.get ~a))
            (else ~a)))))"
          function value function function keys (bootstrap-function-info value 2)
          keys keys
          (b-condition (b-wat "(i32.or (i32.ne (i32.and (local.get ~a) (i32.const 7)) (i32.const 6)) (i32.ne (i32.load8_u (i32.sub (local.get ~a) (i32.const 6))) (i32.const 250)))" keys keys) 4)
          keys keys keys
          (bootstrap-metadata-keyvect (list (make-b-raw-code :text value))))))))
