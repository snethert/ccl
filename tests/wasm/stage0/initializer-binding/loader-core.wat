;; S0-LL15-a loader dependencies (phase 0). Instantiated before any bundle:
;; it owns the event log, the completion ledger in memory and the three
;; loader-level initializers. Bundles import its note/complete/completed
;; services, so no bundle can be instantiated before this module exists.
(module
  (import "env" "memory" (memory 2 2))
  (table (export "entries") 4 4 funcref)
  ;; event log: count at 4096, codes from 4100
  (func $note (export "note") (param $code i32) (local $n i32)
    (local.set $n (i32.load (i32.const 4096)))
    (i32.store (i32.add (i32.const 4100) (i32.mul (local.get $n) (i32.const 4))) (local.get $code))
    (i32.store (i32.const 4096) (i32.add (local.get $n) (i32.const 1))))
  ;; completion words from 1024, execution counters from 1152, one per ordinal
  (func $complete (export "complete") (param $ordinal i32) (param $value i32)
    (i32.store (i32.add (i32.const 1024) (i32.mul (local.get $ordinal) (i32.const 4))) (local.get $value))
    (i32.store (i32.add (i32.const 1152) (i32.mul (local.get $ordinal) (i32.const 4)))
               (i32.add (i32.load (i32.add (i32.const 1152) (i32.mul (local.get $ordinal) (i32.const 4)))) (i32.const 1))))
  (func $completed (export "completed") (param $ordinal i32) (result i32)
    (i32.load (i32.add (i32.const 1024) (i32.mul (local.get $ordinal) (i32.const 4)))))
  (func $require (param $ordinal i32) (param $expected i32) (result i32)
    (i32.eq (call $completed (local.get $ordinal)) (local.get $expected)))
  ;; ordinal 0: memory map and canonical objects
  (func (export "init_map") (result i32)
    (call $note (i32.const 100))
    (i32.store (i32.const 2048) (i32.const 3))                     ;; region count
    (i32.store (i32.const 2052) (i32.const 1024)) (i32.store (i32.const 2056) (i32.const 1312)) (i32.store (i32.const 2060) (i32.const 1))  ;; ledger region
    (i32.store (i32.const 2064) (i32.const 4096)) (i32.store (i32.const 2068) (i32.const 8192)) (i32.store (i32.const 2072) (i32.const 2))  ;; event log
    (i32.store (i32.const 2076) (i32.const 8192)) (i32.store (i32.const 2080) (i32.const 12288)) (i32.store (i32.const 2084) (i32.const 3)) ;; definitions
    ;; canonical NIL: a cons at 77824 whose CDR and CAR are NIL; T at the recorded offset
    (i32.store (i32.const 77824) (i32.const 77825)) (i32.store (i32.const 77828) (i32.const 77825))
    (i32.store (i32.const 77832) (i32.const 1850))
    (call $complete (i32.const 0) (i32.const 19777))
    (i32.const 19777))
  ;; ordinal 1: early diagnostic service; requires the map
  (func (export "init_diagnostics") (result i32)
    (if (i32.eqz (call $require (i32.const 0) (i32.const 19777))) (then (call $note (i32.const 901)) (return (i32.const -1))))
    (call $note (i32.const 101))
    (i32.store (i32.const 1280) (i32.const 1))        ;; error-service mode: EARLY
    (i32.store (i32.const 1284) (i32.const 53670))    ;; fatal sink sentinel
    (call $complete (i32.const 1) (i32.const 17473))
    (i32.const 17473))
  ;; ordinal 2: code-installation service; requires map and diagnostics
  (func (export "init_install") (result i32)
    (if (i32.eqz (i32.and (call $require (i32.const 0) (i32.const 19777)) (call $require (i32.const 1) (i32.const 17473)))) (then (call $note (i32.const 902)) (return (i32.const -1))))
    (call $note (i32.const 102))
    (i32.store (i32.const 1288) (i32.const 4))        ;; installable slot count
    (call $complete (i32.const 2) (i32.const 18771))
    (i32.const 18771)))
