;; S0-ENGINE-a single-thread JSPI profile module: a suspending import called
;; from nested frames with a live local, twice per entry, and once under a
;; tail-called frame. No memory: this profile check is about stack switching.
(module
  (import "host" "io" (func $io (param i32) (result i32)))
  (func $inner (param $x i32) (result i32) (local $keep i32)
    (local.set $keep (i32.mul (local.get $x) (i32.const 3)))
    (i32.add (local.get $keep) (call $io (local.get $x))))
  (func (export "run") (param $x i32) (result i32)
    (i32.add (call $inner (local.get $x)) (call $inner (i32.add (local.get $x) (i32.const 1)))))
  (func (export "run_tail") (param $x i32) (result i32) (return_call $inner (local.get $x))))
