;; Control: init_errors writes a wrong completion value; dependents must be refused.
(module
  (import "env" "memory" (memory 2 2))
  (import "loader" "note" (func $note (param i32)))
  (import "loader" "complete" (func $complete (param i32 i32)))
  (import "loader" "completed" (func $completed (param i32) (result i32)))
  (func (export "init_errors") (result i32)
    (call $note (i32.const 105))
    (i32.store (i32.const 8704) (i32.const 3))
    (call $complete (i32.const 5) (i32.const 1))
    (i32.const 1))
  (func (export "activate_errors") (result i32) (call $note (i32.const 906)) (i32.const -1)))
