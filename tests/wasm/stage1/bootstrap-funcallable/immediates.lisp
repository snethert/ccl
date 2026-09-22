;;; Funcallable instances retain the ordinary callable prefix. Their final
;;; word points to the seven Lisp immediates described by LISPEQU.
(defun bootstrap-function-immediate (forms storep)
  (unless (= (length forms) (if storep 3 2))
    (refuse :funcallable-immediate-arity))
  (bootstrap-operands forms
    (lambda (values)
      (let* ((function (first values)) (index (second values))
             (value (third values)) (vector (temporary)))
        (b-wat "(block (result i32)
                 (local.set ~a (call $object_base
                   (i32.load offset=28 (call $object_base ~a (i32.const 32) (i32.const 1834)))
                   (i32.const 32) (i32.const 2042)))
                 ~a ~a)"
          vector function
          (b-condition (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.ge_u ~a (i32.const 28)))" index index) 4)
          (let ((address (b-wat "(i32.add (local.get ~a) (i32.add (i32.const 4) ~a))" vector index)))
            (if storep (b-wat "(i32.store ~a ~a) ~a" address value value)
                (b-wat "(i32.load ~a)" address))))))))

(defun bootstrap-make-funcallable (forms)
  (unless (= (length forms) 2) (refuse :funcallable-constructor-arity))
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (function immediates) values
        (b-wat "(block (result i32)
          (drop (call $object_base ~a (i32.const 32) (i32.const 1578)))
          (drop (call $object_base ~a (i32.const 32) (i32.const 2042)))
          (i32.add ~a (i32.const 38)))"
          function immediates
          (b-heap-block 64
            (lambda (base)
              ;; Assurance precedes these loads. Both operands are rooted,
              ;; and every field is initialized before publication.
              (b-wat "(memory.copy ~a (i32.sub ~a (i32.const 6)) (i32.const 32))
                      (memory.copy (i32.add ~a (i32.const 32)) (i32.sub ~a (i32.const 6)) (i32.const 32))
                      (i32.store (i32.add ~a (i32.const 32)) (i32.const 1834))
                      (i32.store (i32.add ~a (i32.const 60)) (i32.add ~a (i32.const 6)))"
                     base immediates base function base base base))))))))
