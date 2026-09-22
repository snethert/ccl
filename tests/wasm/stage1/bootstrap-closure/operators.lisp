;;; Operands are rooted before a later operand can allocate. Accessors below
;;; perform their checks before storing, and contain no intervening safepoint.
(defun bootstrap-shift (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (count value) values
        (b-wat "~a ~a ~a"
               (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" count count) 5)
               (b-condition (b-wat "(i32.and ~a (i32.const 3))" value) 5)
               (if (eq op 'ccl::%ilsl)
                 (b-wat "(if (result i32) (i32.ge_u ~a (i32.const 120)) (then (i32.const 0)) (else (i32.shl ~a (i32.shr_u ~a (i32.const 2)))))" count value count)
                 (b-wat "(i32.and (if (result i32) (i32.ge_u ~a (i32.const 128)) (then ~a) (else (i32.~a ~a (i32.shr_u ~a (i32.const 2))))) (i32.const -4))"
                        count (if (eq op 'ccl::%iasr) (b-wat "(i32.shr_s ~a (i32.const 31))" value) "(i32.const 0)")
                        (if (eq op 'ccl::%iasr) "shr_s" "shr_u") value count)))))))

(defun bootstrap-uvector-access (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (let* ((object (first values)) (index (second values))
             (value (third values)) (tag (temporary))
             (raw (mapcar (lambda (x) (make-b-raw-code :text x)) values)))
        (b-wat "(local.set ~a ~a)
                 (if (result i32) (i32.eq (local.get ~a) (i32.const 764))
                   (then ~a)
                   (else (if (result i32) (i32.eq (local.get ~a) (i32.const 796))
                     (then ~a) (else ~a))))"
               tag (bootstrap-typecode object) tag
               (bootstrap-string-access (if value 'ccl::%set-sbchar 'ccl::%sbchar) raw)
               tag
               (bootstrap-typed-access (if value 'ccl::%typed-uvset 'ccl::%typed-uvref)
                 (cons (bootstrap-constant :unsigned-8-bit-vector) raw))
               (bootstrap-node-access (if (eq op 'ccl::uvset) 'ccl::%svset 'ccl::%svref) raw))))))

(defun bootstrap-heap-block (bytes emit)
  (let ((size (temporary)) (base (temporary)))
    (b-wat "(block (result i32) (local.set ~a ~a) ~a
             (local.set ~a ~a) ~a ~a ~a ~a ~a (local.get ~a))"
           size bytes
           (if *b-allocation-retry*
             (b-wat "(if (i64.gt_u (i64.add (i64.extend_i32_u ~a) (i64.extend_i32_u (local.get ~a))) (i64.extend_i32_u ~a)) (then (call $heap_ensure (local.get ~a))))"
                    (b-load wasm32::tcr.alloc_pointer) size (b-load wasm32::tcr.alloc_limit) size) "")
           base (b-load wasm32::tcr.alloc_pointer)
           (b-condition (b-wat "(i32.or (i32.lt_u (local.get ~a) ~a) (i32.and (local.get ~a) (i32.const 7)))" base (b-load wasm32::tcr.alloc_base) base) 6)
           (b-condition (b-wat "(i64.gt_u (i64.extend_i32_u ~a) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16)))" (b-load wasm32::tcr.alloc_limit)) 6)
           (b-condition (b-wat "(i64.gt_u (i64.add (i64.extend_i32_u (local.get ~a)) (i64.extend_i32_u (local.get ~a))) (i64.extend_i32_u ~a))" base size (b-load wasm32::tcr.alloc_limit)) 6)
           (funcall emit (b-local base) (b-local size))
           (b-store wasm32::tcr.alloc_pointer (b-wat "(i32.add (local.get ~a) (local.get ~a))" base size)) base)))

(defun bootstrap-make-vector (forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (count tag &optional initial) values
        (let ((i (temporary)) (n (temporary)) (kind (temporary)))
          (with-output-to-string (s)
            (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.gt_u ~a (i32.const 67108860)))" count count) 6) s)
            (format s "(local.set ~a (i32.shr_u ~a (i32.const 2))) (local.set ~a ~a)" n count kind tag)
            (write-string (b-condition (b-wat "(i32.and (i32.ne ~a (i32.const 1000)) (i32.and (i32.ne ~a (i32.const 764)) (i32.ne ~a (i32.const 796))))" tag tag tag) 4) s)
            (when initial
              (format s "(if (i32.eq (local.get ~a) (i32.const 764)) (then ~a)) (if (i32.eq (local.get ~a) (i32.const 796)) (then ~a))"
                      kind (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 255)) (i32.const 75))" initial) 5)
                      kind (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 1024)))" initial initial) 5)))
            (write-string
             (b-wat "(i32.add ~a (i32.const 6))"
               (bootstrap-heap-block
                (b-wat "(i32.and (i32.add (if (result i32) (i32.eq (local.get ~a) (i32.const 796)) (then (local.get ~a)) (else (i32.shl (local.get ~a) (i32.const 2)))) (i32.const 11)) (i32.const -8))" kind n n)
                (lambda (base bytes)
                  (b-wat "(memory.fill ~a (i32.const 0) ~a)
                           (i32.store ~a (i32.or (i32.shl (local.get ~a) (i32.const 8)) (i32.shr_u (local.get ~a) (i32.const 2))))
                           (local.set ~a (i32.const 0))
                           (block $vector_done (loop $vector_fill
                             (br_if $vector_done (i32.ge_u (local.get ~a) (local.get ~a)))
                             (if (i32.eq (local.get ~a) (i32.const 796))
                               (then (i32.store8 (i32.add ~a (i32.add (i32.const 4) (local.get ~a))) ~a))
                               (else (i32.store (i32.add ~a (i32.add (i32.const 4) (i32.shl (local.get ~a) (i32.const 2)))) ~a)))
                             (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $vector_fill)))"
                         base bytes base n kind i i n kind base i
                         (if initial (b-wat "(i32.shr_u ~a (i32.const 2))" initial) "(i32.const 0)")
                         base i
                         (b-wat "(if (result i32) (i32.eq (local.get ~a) (i32.const 1000)) (then ~a) (else ~a))"
                                kind (or initial "(i32.const 77825)")
                                (if initial (b-wat "(i32.shr_u ~a (i32.const 8))" initial) "(i32.const 0)")) i i)))) s)))))))

(defun bootstrap-make-list (forms)
  (bootstrap-operands forms
    (lambda (values)
      (let ((count (first values)) (value (second values))
            (i (temporary)) (head (temporary)))
        (b-wat "~a (local.set ~a (i32.const 77825)) (drop ~a) (local.get ~a)"
               (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))" count count) 6)
               head
               (bootstrap-heap-block (b-wat "(i32.shl ~a (i32.const 1))" count)
                 (lambda (base bytes)
                   (b-wat "(local.set ~a (i32.const 0))
                            (block $list_done (loop $list_fill
                              (br_if $list_done (i32.ge_u (local.get ~a) ~a))
                              (i32.store (i32.add ~a (local.get ~a)) (local.get ~a))
                              (i32.store offset=4 (i32.add ~a (local.get ~a)) ~a)
                              (local.set ~a (i32.add (i32.add ~a (local.get ~a)) (i32.const 1)))
                              (local.set ~a (i32.add (local.get ~a) (i32.const 8))) (br $list_fill)))"
                          i i bytes base i head base i value head base i i i))) head)))))

(defun bootstrap-lexpr (var start body)
  (when (b-captured-p var) (refuse :escaping-lexpr))
  (let ((count (temporary)) (i (temporary)))
    (b-wat "(local.set ~a (if (result i32) (i32.gt_u (local.get $nargs) (i32.const ~d)) (then (i32.sub (local.get $nargs) (i32.const ~d))) (else (i32.const 0)))) ~a"
           count start start
           (b-retained-frame (b-wat "(i32.add (local.get ~a) (i32.const 1))" count)
             (lambda (root)
               (concatenate 'string
                 (b-wat "(i32.store offset=8 ~a (i32.shl (local.get ~a) (i32.const 2)))
                          (local.set ~a (i32.const 0))
                          (block $lexpr_done (loop $lexpr_copy
                            (br_if $lexpr_done (i32.ge_u (local.get ~a) (local.get ~a)))
                            (i32.store (i32.add ~a (i32.add (i32.const 8) (i32.shl (i32.sub (local.get ~a) (local.get ~a)) (i32.const 2))))
                              (i32.load (i32.add (local.get $incoming) (i32.shl (i32.add (local.get ~a) (i32.const ~d)) (i32.const 2)))))
                            (local.set ~a (i32.add (local.get ~a) (i32.const 1))) (br $lexpr_copy)))"
                        root count i i count root count i i start i i)
                 (b-bind-value var (b-at root 8))
                 (funcall body)))))))

(defun bootstrap-box-word (word signed)
  (let ((n (temporary)))
    (b-wat "(block (result i32) (local.set ~a ~a)
             (if (result i32) ~a
               (then (i32.shl (local.get ~a) (i32.const 2)))
               (else ~a)))"
           n word
           (if signed
             (b-wat "(i32.and (i32.ge_s (local.get ~a) (i32.const -536870912)) (i32.le_s (local.get ~a) (i32.const 536870911)))" n n)
             (b-wat "(i32.le_u (local.get ~a) (i32.const 536870911))" n)) n
           (let ((one (b-wat "(i32.add ~a (i32.const 6))"
                        (b-heap-block 8 (lambda (base)
                          (b-wat "(i32.store ~a (i32.const 263)) (i32.store offset=4 ~a (local.get ~a))" base base n))))))
             (if signed one
               (b-wat "(if (result i32) (i32.lt_u (local.get ~a) (i32.const 2147483648)) (then ~a) (else (i32.add ~a (i32.const 6))))"
                      n one (b-heap-block 16 (lambda (base)
                              (b-wat "(i32.store ~a (i32.const 519)) (i32.store offset=4 ~a (local.get ~a)) (i32.store offset=8 ~a (i32.const 0)) (i32.store offset=12 ~a (i32.const 0))" base base n base base)))))))))

(defun bootstrap-typed-access (op args)
  (let* ((kind (ccl::acode-immediate-operand (car args)))
         (layout (assoc kind '((:unsigned-8-bit-vector 1 nil 199 0 255)
                              (:signed-8-bit-vector 1 t 207 -128 127)
                              (:unsigned-16-bit-vector 2 nil 215 0 65535)
                              (:signed-16-bit-vector 2 t 223 -32768 32767)
                              (:unsigned-32-bit-vector 4 nil 167 0 536870911)
                              (:signed-32-bit-vector 4 t 175 -536870912 536870911)
                              (:fixnum-vector 4 t 183 -536870912 536870911)))))
    (case kind
      (:simple-vector
       (return-from bootstrap-typed-access
         (bootstrap-node-access (if (eq op 'ccl::%typed-uvset) 'ccl::svset 'ccl::svref) (cdr args))))
      (:simple-string
       (return-from bootstrap-typed-access
         (bootstrap-string-access (if (eq op 'ccl::%typed-uvset) 'ccl::%set-sbchar 'ccl::%sbchar) (cdr args)))))
    (unless layout (refuse :bootstrap-array-kind))
    (destructuring-bind (kind width signed subtag low high) layout
      (bootstrap-operands (cdr args)
        (lambda (values)
          (destructuring-bind (object index &optional value) values
            (let ((base (temporary)) (header (temporary)))
              (with-output-to-string (s)
                (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
                (format s "(local.set ~a (i32.sub ~a (i32.const 6))) (call $span (local.get ~a) (i32.const 4)) (local.set ~a (i32.load (local.get ~a)))" base object base header base)
                ;; %SCHARCODE deliberately uses CCL's unsigned-word view of a
                ;; string. Both representations have exactly four bytes per cell.
                (write-string (b-condition
                  (if (eq kind :unsigned-32-bit-vector)
                    (b-wat "(i32.and (i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const ~d)) (i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 191)))" header subtag header)
                    (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const ~d))" header subtag)) 4) s)
                (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
                (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.mul (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const ~d))))" base header width)
                (let ((address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) (i32.mul (i32.shr_u ~a (i32.const 2)) (i32.const ~d))))" base index width)))
                  (if value
                    (progn
                      (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.or (i32.lt_s ~a (i32.const ~d)) (i32.gt_s ~a (i32.const ~d))))" value value (* 4 low) value (* 4 high)) 5) s)
                      (format s "(i32.store~a ~a ~a) ~a" (case width (1 "8") (2 "16") (t "")) address
                              (if (eq kind :fixnum-vector) value (b-wat "(i32.shr_s ~a (i32.const 2))" value)) value))
                    (let ((read (b-wat "(i32.load~a ~a)" (case width (1 (if signed "8_s" "8_u")) (2 (if signed "16_s" "16_u")) (t "")) address)))
                      (write-string (cond ((eq kind :fixnum-vector) read)
                                          ((= width 4) (bootstrap-box-word read signed))
                                          (t (b-wat "(i32.shl ~a (i32.const 2))" read))) s))))))))))))
