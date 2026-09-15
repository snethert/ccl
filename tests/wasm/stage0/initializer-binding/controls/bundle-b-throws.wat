;; Control: init_errors raises a Wasm exception after a partial write.
(module
  (import "env" "memory" (memory 2 2))
  (import "loader" "note" (func $note (param i32)))
  (import "loader" "complete" (func $complete (param i32 i32)))
  (import "loader" "completed" (func $completed (param i32) (result i32)))
  (tag $failure)
  (func (export "init_errors") (result i32) (call $note (i32.const 105)) (i32.store (i32.const 8704) (i32.const 3)) (throw $failure))
  (func (export "activate_errors") (result i32) (call $note (i32.const 906)) (i32.const -1)))
