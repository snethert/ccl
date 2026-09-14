(module
  (import "env" "memory" (memory 1 1 shared))
  (func (export "entry") (param $x i32) (result i32)
    (i32.add (i32.load (i32.const 8192)) (local.get $x)))
)
