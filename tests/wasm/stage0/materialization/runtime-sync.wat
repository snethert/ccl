;; Precompiled-callback runtime: emitted for unshared memory. request completes
;; synchronously in Wasm; no suspension path and no wait instruction.
(module
  (import "env" "memory" (memory 1 4))
  (func (export "request") (param $x i32) (result i32)
    (i32.store (i32.const 512) (local.get $x))
    (i32.mul (local.get $x) (i32.const 2))))
