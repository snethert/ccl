;; Full-profile runtime: emitted for shared memory. request publishes the
;; argument, raises the flag and blocks in memory.atomic.wait32 until the
;; supervisor stores the answer and notifies.
(module
  (import "env" "memory" (memory 1 4 shared))
  (func (export "request") (param $x i32) (result i32)
    (i32.store (i32.const 512) (local.get $x))
    (i32.atomic.store (i32.const 516) (i32.const 1))
    (drop (memory.atomic.wait32 (i32.const 520) (i32.const 0) (i64.const -1)))
    (i32.atomic.store (i32.const 520) (i32.const 0))
    (i32.load (i32.const 524))))
