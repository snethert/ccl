;; Control: init_compiler completes correctly but overwrites the error system's
;; completion word, so the next dependent's prerequisite check must refuse.
(module
  (import "env" "memory" (memory 2 2))
  (import "loader" "note" (func $note (param i32)))
  (import "loader" "complete" (func $complete (param i32 i32)))
  (import "loader" "completed" (func $completed (param i32) (result i32)))
  (func $require (param $ordinal i32) (param $expected i32) (result i32) (i32.eq (call $completed (local.get $ordinal)) (local.get $expected)))
  (func (export "init_compiler") (result i32)
    (if (i32.eqz (i32.and (call $require (i32.const 5) (i32.const 17746)) (i32.eq (i32.load (i32.const 1280)) (i32.const 1))))
      (then (call $note (i32.const 907)) (return (i32.const -1))))
    (call $note (i32.const 107))
    (i32.store (i32.const 8960) (i32.const 2)) (i32.store (i32.const 8964) (i32.const 8708)) (i32.store (i32.const 8968) (i32.const 8712))
    (call $complete (i32.const 7) (i32.const 17229))
    (i32.store (i32.const 1044) (i32.const 7))
    (i32.const 17229))
  (func (export "finalize") (result i32) (call $note (i32.const 908)) (i32.const -1)))
