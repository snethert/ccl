;; Definitions bundle B: the error system (ordinal 5) and its activation
;; (ordinal 6, phase 2). Activation flips the service mode from EARLY to FULL
;; only after the compiler stubs exist, so the early failure path stays usable
;; while definitions are installed.
(module
  (import "env" "memory" (memory 2 2))
  (import "loader" "note" (func $note (param i32)))
  (import "loader" "complete" (func $complete (param i32 i32)))
  (import "loader" "completed" (func $completed (param i32) (result i32)))
  (func $require (param $ordinal i32) (param $expected i32) (result i32) (i32.eq (call $completed (local.get $ordinal)) (local.get $expected)))
  (func (export "init_errors") (result i32)
    (if (i32.eqz (i32.and (i32.and (call $require (i32.const 3) (i32.const 21337)) (call $require (i32.const 4) (i32.const 21060))) (i32.eq (i32.load (i32.const 1280)) (i32.const 1))))
      (then (call $note (i32.const 905)) (return (i32.const -1))))
    (call $note (i32.const 105))
    (i32.store (i32.const 8704) (i32.const 3)) (i32.store (i32.const 8708) (i32.const 8196)) (i32.store (i32.const 8712) (i32.const 8200)) (i32.store (i32.const 8716) (i32.const 8204))
    (call $complete (i32.const 5) (i32.const 17746))
    (i32.const 17746))
  (func (export "activate_errors") (result i32)
    (if (i32.eqz (i32.and (i32.and (call $require (i32.const 5) (i32.const 17746)) (call $require (i32.const 7) (i32.const 17229))) (i32.eq (i32.load (i32.const 1280)) (i32.const 1))))
      (then (call $note (i32.const 906)) (return (i32.const -1))))
    (call $note (i32.const 106))
    (i32.store (i32.const 1280) (i32.const 2))        ;; error-service mode: FULL
    (call $complete (i32.const 6) (i32.const 16707))
    (i32.const 16707)))
