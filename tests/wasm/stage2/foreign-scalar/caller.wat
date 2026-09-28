(module
  (import "env" "failure" (tag $failure (param i32)))
  (import "env" "call" (func $call))
  (global $cleanups (mut i32) (i32.const 0))
  (func (export "cleanups") (result i32) global.get $cleanups)
  (func (export "run") (result i32) (local $result i32)
    (block $caught (result i32)
      (try_table (catch $failure $caught)
        call $call)
      i32.const 0)
    local.set $result
    global.get $cleanups i32.const 1 i32.add global.set $cleanups
    local.get $result)
)
