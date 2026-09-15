;; S0-LL21-c canonical Lisp-code template. One unshared wasm32 memory import
;; with explicit limits; materialization flips only that flag byte. The code
;; calls the profile runtime's request import, so the same bytes execute under
;; the full (wait-based), single-thread JSPI and precompiled-callback runtimes.
;; No wait or notify instruction may appear in a template.
(module
  (import "env" "memory" (memory 1 4))
  (import "runtime" "request" (func $request (param i32) (result i32)))
  (func $work (param $x i32) (result i32 i32) (local $serial i32)
    (local.set $serial (i32.atomic.rmw.add (i32.const 640) (i32.const 1)))
    (i32.add (i32.add (call $request (local.get $x)) (local.get $serial)) (i32.const 1))
    (i32.const 2))
  (func (export "entry") (param $x i32) (result i32 i32)
    (return_call $work (local.get $x)))
  (func (export "grow") (param $pages i32) (result i32) (memory.grow (local.get $pages)))
  (func (export "size") (result i32) (memory.size)))
