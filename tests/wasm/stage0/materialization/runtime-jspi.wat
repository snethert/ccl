;; Single-thread JSPI runtime: emitted for unshared memory. request forwards to
;; a suspending host import; suspension is engine stack switching through the
;; WebAssembly.Suspending import. No wait instruction may appear here.
(module
  (import "env" "memory" (memory 1 4))
  (import "host" "io" (func $io (param i32) (result i32)))
  (func (export "request") (param $x i32) (result i32)
    (i32.store (i32.const 512) (local.get $x))
    (call $io (local.get $x))))
