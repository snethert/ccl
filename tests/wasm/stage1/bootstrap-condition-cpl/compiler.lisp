(in-package :wasm32-compiler)

;;; The owner supplies native class cells, not ancestry bits. The vector and
;;; cells are image roots; their class objects and CPLs may move. Resolve a
;;; cell afresh at each test, then call CCL's ordinary class predicate.
(defun bootstrap-condition-class-p (type)
  (and (symbolp type) (find-class type nil) (subtypep type 'condition)))

(defun bootstrap-condition-class (type)
  (unless (bootstrap-condition-class-p type)
    (refuse :b-condition-type))
  type)

(defun bootstrap-condition-typep (object type)
  (setq *b-condition-used* t)
  (pushnew "condition_class_cells" *b-symbols* :test #'equal)
  (bootstrap-true-p
    (bootstrap-predicate-call 'ccl::class-typep
      (list (make-b-raw-code :text object)
            (make-b-raw-code :text
              (b-wat "(call $condition_class ~a)" type))))))

(defun bootstrap-condition-class-runtime ()
  "(func $condition_class (param $name i32) (result i32)
    (local $p i32) (local $n i32) (local $i i32) (local $cell i32) (local $class i32)
    (if (i32.ne (i32.and (global.get $symbol_condition_class_cells) (i32.const 7)) (i32.const 6))
      (then (throw $call_error (i32.const 12))))
    (local.set $p (i32.sub (global.get $symbol_condition_class_cells) (i32.const 6)))
    (call $span (local.get $p) (i32.const 4))
    (if (i32.ne (i32.and (i32.load (local.get $p)) (i32.const 255)) (i32.const 250))
      (then (throw $call_error (i32.const 12))))
    (local.set $n (i32.shr_u (i32.load (local.get $p)) (i32.const 8)))
    (call $span (local.get $p) (i32.mul (i32.add (local.get $n) (i32.const 1)) (i32.const 4)))
    (block $missing (loop $cells
      (br_if $missing (i32.ge_u (local.get $i) (local.get $n)))
      (local.set $cell (call $handler_cons
        (i32.load (i32.add (local.get $p) (i32.add (i32.const 4) (i32.mul (local.get $i) (i32.const 4)))))))
      (if (i32.eq (i32.load offset=4 (local.get $cell)) (local.get $name))
        (then (local.set $class (i32.load (local.get $cell)))
          (drop (call $object_base (local.get $class) (i32.const 16) (i32.const 882)))
          (return (local.get $class))))
      (local.set $i (i32.add (local.get $i) (i32.const 1))) (br $cells)))
    (throw $call_error (i32.const 12)))")
