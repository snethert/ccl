;; Wrong runtime for an unshared profile: declares unshared memory but waits.
(module
  (import "env" "memory" (memory 1 4))
  (func (export "request") (param $x i32) (result i32)
    (drop (memory.atomic.wait32 (i32.const 520) (i32.const 0) (i64.const 1000)))
    (i32.mul (local.get $x) (i32.const 2))))
