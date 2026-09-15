;; Control: bundle B without its init_errors initializer export.
(module
  (import "env" "memory" (memory 2 2))
  (import "loader" "note" (func $note (param i32)))
  (import "loader" "complete" (func $complete (param i32 i32)))
  (import "loader" "completed" (func $completed (param i32) (result i32)))
  (func (export "activate_errors") (result i32) (call $note (i32.const 906)) (i32.const -1)))
