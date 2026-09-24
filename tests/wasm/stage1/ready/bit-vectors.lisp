;;; Packed bits use the native x8632 low-bit-first representation. Validate
;;; every operand before storing; a byte access does not touch tail padding.
(defun bootstrap-bit-access (forms)
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (object index &optional value) values
        (let ((base (temporary)) (header (temporary))
              (address (temporary)) (mask (temporary)))
          (with-output-to-string (s)
            (write-string (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4) s)
            (format s "(local.set ~a (i32.sub ~a (i32.const 6)))
                       (call $span (local.get ~a) (i32.const 4))
                       (local.set ~a (i32.load (local.get ~a)))" base object base header base)
            (write-string (b-condition (b-wat "(i32.ne (i32.and (local.get ~a) (i32.const 255)) (i32.const 255))" header) 4) s)
            (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u (i32.shr_u ~a (i32.const 2)) (i32.shr_u (local.get ~a) (i32.const 8))))" index index header) 4) s)
            (format s "(call $span (local.get ~a) (i32.add (i32.const 4) (i32.shr_u (i32.add (i32.shr_u (local.get ~a) (i32.const 8)) (i32.const 7)) (i32.const 3))))
                       (local.set ~a (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 5)))))
                       (local.set ~a (i32.shl (i32.const 1) (i32.and (i32.shr_u ~a (i32.const 2)) (i32.const 7))))"
                    base header address base index mask index)
            (if value
              (progn
                (write-string (b-wat "(if ~a (then ~a))"
                  (b-wat "(i32.and (i32.ne ~a (i32.const 0)) (i32.ne ~a (i32.const 4)))" value value)
                  (b-type-failure value 'bit)) s)
                (format s "(i32.store8 (local.get ~a)
                             (i32.or (i32.and (i32.load8_u (local.get ~a)) (i32.xor (local.get ~a) (i32.const -1)))
                                     (if (result i32) ~a (then (local.get ~a)) (else (i32.const 0))))) ~a"
                        address address mask value mask value))
              (format s "(i32.shl (i32.ne (i32.and (i32.load8_u (local.get ~a)) (local.get ~a)) (i32.const 0)) (i32.const 2))"
                      address mask))))))))

(defun bootstrap-bit-vector (values)
  (destructuring-bind (count tag &optional initial) values
    (declare (ignore tag))
    (let ((n (temporary)) (payload (temporary)))
      (with-output-to-string (s)
        (write-string (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.gt_u ~a (i32.const 67108860)))" count count) 6) s)
        (when initial
          (write-string (b-wat "(if ~a (then ~a))"
                  (b-wat "(i32.and (i32.ne ~a (i32.const 0)) (i32.ne ~a (i32.const 4)))" initial initial)
                  (b-type-failure initial 'bit)) s))
        (format s "(local.set ~a (i32.shr_u ~a (i32.const 2)))
                   (local.set ~a (i32.shr_u (i32.add (local.get ~a) (i32.const 7)) (i32.const 3)))"
                n count payload n)
        (write-string
         (b-wat "(i32.add ~a (i32.const 6))"
           (bootstrap-heap-block
            (b-wat "(i32.and (i32.add (local.get ~a) (i32.const 11)) (i32.const -8))" payload)
            (lambda (base bytes)
              (b-wat "(memory.fill ~a (i32.const 0) ~a)
                       (i32.store ~a (i32.or (i32.shl (local.get ~a) (i32.const 8)) (i32.const 255)))
                       (memory.fill (i32.add ~a (i32.const 4)) ~a (local.get ~a))
                       (if (i32.and (local.get ~a) (i32.const 7))
                         (then (i32.store8 (i32.add ~a (i32.add (i32.const 3) (local.get ~a)))
                                 (i32.and ~a (i32.sub (i32.shl (i32.const 1) (i32.and (local.get ~a) (i32.const 7))) (i32.const 1))))))"
                     base bytes base n base
                     (if initial (b-wat "(i32.sub (i32.const 0) (i32.shr_u ~a (i32.const 2)))" initial) "(i32.const 0)") payload
                     n base payload
                     (if initial (b-wat "(i32.sub (i32.const 0) (i32.shr_u ~a (i32.const 2)))" initial) "(i32.const 0)") n)))) s)))))

(defun bootstrap-make-bit-array (forms)
  (when (and forms (evenp (length (cdr forms))))
    (let ((initial nil) (seen nil) (bitp nil))
      (loop for (key value) on (cdr forms) by #'cddr do
        (multiple-value-bind (name constant) (bootstrap-immediate key)
          (unless (and constant (member name '(:element-type :initial-element))
                       (not (member name seen)))
            (return-from bootstrap-make-bit-array nil))
          (push name seen)
          (if (eq name :initial-element)
            (setq initial value)
            (multiple-value-bind (type constant) (bootstrap-immediate value)
              (unless (and constant (eq type 'bit))
                (return-from bootstrap-make-bit-array nil))
              (setq bitp t)))))
      (when bitp
        (b-multiple (make-b-raw-code :text
          (bootstrap-make-vector
           (append (list (first forms) (bootstrap-constant wasm32::subtag-bit-vector))
                   (when initial (list initial))))))))))
