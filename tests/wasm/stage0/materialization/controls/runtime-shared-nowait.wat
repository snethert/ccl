;; Wrong runtime for an unshared profile: declares shared memory without waiting.
(module
  (import "env" "memory" (memory 1 4 shared))
  (func (export "request") (param $x i32) (result i32) (i32.mul (local.get $x) (i32.const 2))))
