;; Synthetic B entry for the service's directed refusals and moving-root cases.
;; Ordinary compiled Lisp is independently exercised after READY.
(module
 (import "host" "run" (func $run (param i32 i32) (result i32 i32)))
 (func (export "entry") (param i32 i32) (result i32 i32)
  local.get 0 local.get 1 call $run))
