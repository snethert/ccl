;; S0-ENGINE-a feature module. Canonical template: unshared wasm32 memory import
;; with explicit limits. The shared variant differs only in the memory flag.
;; Multivalue, tail calls, final exception handling (try_table, exnref,
;; throw_ref), bulk memory and atomics in one hand-built module.
(module
  (type $sig (func (param i32 i32) (result i32)))
  (import "env" "memory" (memory 1 4))
  (import "host" "fail" (func $fail))
  (tag $lisp (param i32))
  (tag $other (param i32))
  (export "lisp" (tag $lisp))
  (table $t 2 2 funcref)
  (elem (i32.const 0) $tail_indirect)
  (data $seed "ENGINE-MATRIX-SEED-2026")

  ;; multivalue: ordered unequal results from a function and from a block
  (func (export "pair") (param $a i32) (result i32 i32)
    (local.get $a) (i32.add (local.get $a) (i32.const 1)))
  (func (export "block_pair") (param $a i32) (result i32)
    block (result i32 i32) local.get $a i32.const 3 end
    i32.sub)

  ;; tail calls: direct and indirect chains of depth $n with an accumulator
  (func $tail (export "tail") (param $n i32) (param $acc i32) (result i32)
    (if (result i32) (i32.eqz (local.get $n))
      (then (local.get $acc))
      (else (return_call $tail (i32.sub (local.get $n) (i32.const 1)) (i32.add (local.get $acc) (i32.const 1))))))
  (func $tail_indirect (export "tail_indirect") (param $n i32) (param $acc i32) (result i32)
    (if (result i32) (i32.eqz (local.get $n))
      (then (local.get $acc))
      (else (return_call_indirect (type $sig) (i32.sub (local.get $n) (i32.const 1)) (i32.add (local.get $acc) (i32.const 1)) (i32.const 0)))))

  ;; exception handling: payload through a middle frame that records passage
  ;; and rethrows the same exception with throw_ref
  (func $thrower (param $p i32) (throw $lisp (local.get $p)))
  (func $middle (param $p i32) (result i32) (local $e exnref)
    (block $h (result i32 exnref)
      (try_table (catch_ref $lisp $h) (call $thrower (local.get $p)))
      (i32.const -1) (ref.null exn))
    (local.set $e)
    (drop)
    (i32.store (i32.const 64) (i32.add (i32.load (i32.const 64)) (i32.const 1)))
    (throw_ref (local.get $e)))
  (func (export "eh_nested") (param $p i32) (result i32)
    (block $h (result i32)
      (try_table (catch $lisp $h) (drop (call $middle (local.get $p))))
      (i32.const -2)))
  (func (export "passages") (result i32) (i32.load (i32.const 64)))
  (func (export "eh_catch_all") (result i32)
    (block $all
      (block $h (result i32)
        (try_table (catch $lisp $h) (catch_all $all) (throw $other (i32.const 5)))
        (i32.const -4))
      (return))
    (i32.const 7777))
  (func (export "raise") (throw $lisp (i32.const 31337)))
  (func (export "catch_js") (result i32)
    (block $h (try_table (catch_all $h) (call $fail)) (return (i32.const 0)))
    (i32.const 1))
  (func (export "rethrow_js") (local $caught exnref)
    (block $h (result exnref) (try_table (catch_all_ref $h) (call $fail)) (return))
    (local.set $caught)
    (throw_ref (local.get $caught)))

  ;; bulk memory: passive segment, init, copy, fill, drop
  (func (export "bulk")
    (memory.init $seed (i32.const 128) (i32.const 0) (i32.const 23))
    (memory.copy (i32.const 160) (i32.const 128) (i32.const 23))
    (memory.fill (i32.const 192) (i32.const 90) (i32.const 8)))
  (func (export "drop_seed") (data.drop $seed))
  (func (export "reinit") (memory.init $seed (i32.const 128) (i32.const 0) (i32.const 23)))
  (func (export "grow") (param $pages i32) (result i32) (memory.grow (local.get $pages)))
  (func (export "size") (result i32) (memory.size))

  ;; atomics: read-modify-write, compare-exchange, load/store, wait and notify
  (func (export "rmw_add") (param $a i32) (param $v i32) (result i32) (i32.atomic.rmw.add (local.get $a) (local.get $v)))
  (func (export "cmpxchg") (param $a i32) (param $expected i32) (param $new i32) (result i32)
    (i32.atomic.rmw.cmpxchg (local.get $a) (local.get $expected) (local.get $new)))
  (func (export "load") (param $a i32) (result i32) (i32.atomic.load (local.get $a)))
  (func (export "store") (param $a i32) (param $v i32) (i32.atomic.store (local.get $a) (local.get $v)))
  (func (export "wait") (param $a i32) (param $expected i32) (param $timeout i64) (result i32)
    (memory.atomic.wait32 (local.get $a) (local.get $expected) (local.get $timeout)))
  (func (export "notify") (param $a i32) (param $count i32) (result i32)
    (memory.atomic.notify (local.get $a) (local.get $count))))
