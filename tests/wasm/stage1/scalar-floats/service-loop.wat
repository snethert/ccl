;; Measurement only: one pre-existing root frame, 64 ordinary scalar operations.
;; This omits the generated language loop, temporary-frame and value-return code.
(module
 (import "env" "memory" (memory 1 32769 shared))
 (import "floating" "calculate" (func $calculate (param i32 i32 i32) (result i32)))
 (func (export "run") (param $root i32) (param $op i32) (param $safe i32) (param $n i32) (result i32)
  (loop $again
   (i32.store offset=16 (local.get $root) (i32.const 77825))
   (drop (call $calculate (local.get $op) (local.get $root) (local.get $safe)))
   (local.set $n (i32.sub (local.get $n) (i32.const 1))) (br_if $again (local.get $n)))
  (i32.load offset=16 (local.get $root))))
