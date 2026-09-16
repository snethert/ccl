;; S0-LL19-a: exception transfer through nested emitted frames.
;;
;; Every Lisp-shaped function has the B entry shape (self, nargs) -> (value0,
;; nvalues); arguments live at the incoming VSP. A fixture TCR at 256 holds
;; VSP/TSP/CSP, one dynamic binding cell, the root-record head, the handler
;; depth, the cleanup and post-exit counters, the caller-owned result region
;; descriptor, the values-in-transit region and an event log. Each frame
;; pushes a frame record and a root record on TSP, binds the dynamic cell,
;; and pops/restores on ordinary return and on nonlocal exit. Frames with
;; cleanup push a cleanup record on CSP and use try_table catch_all_ref /
;; throw_ref so the cleanup runs exactly once and the same exception
;; continues outward. Values in transit live in the TCR transit region;
;; cleanups write their own values into their frame's region.
(module
  (import "env" "memory" (memory 1 1))
  (type $lisp_entry (func (param i32 i32) (result i32 i32)))
  (type $handler (func (param i32)))
  (tag $lisp (param i32))        ;; nonlocal exit carrying the transit count
  (tag $other (param i32))       ;; a second exit raised by a cleanup
  (tag $unhandled (param i32))   ;; no handler in the Lisp frames
  (tag $condition (param i32))   ;; error signalled by a recoverable check
  (tag $use_value (param i32))   ;; restart transfer back to the check site
  (export "lisp" (tag $lisp)) (export "other" (tag $other)) (export "unhandled" (tag $unhandled)) (export "condition" (tag $condition))
  (table $handlers 2 2 funcref)
  (elem (i32.const 0) $use_value_handler $declining_handler)

  ;; TCR field offsets from 256
  (global $tcr i32 (i32.const 256))
  ;; +0 vsp  +4 tsp  +8 csp  +12 special  +16 root_head  +20 handler_depth
  ;; +24 cleanup_count  +28 post_exit_effects  +32 mv_base  +36 mv_count
  ;; +40 transit_base  +44 transit_count  +48 handler_calls  +52 event_count
  ;; +56 max_handler_depth  +60 resumed
  (func $ld (param $off i32) (result i32) (i32.load (i32.add (global.get $tcr) (local.get $off))))
  (func $st (param $off i32) (param $v i32) (i32.store (i32.add (global.get $tcr) (local.get $off)) (local.get $v)))
  (func $bump (param $off i32) (call $st (local.get $off) (i32.add (call $ld (local.get $off)) (i32.const 1))))
  (func $event (param $code i32)
    (i32.store (i32.add (i32.const 20480) (i32.mul (call $ld (i32.const 52)) (i32.const 4))) (local.get $code))
    (call $bump (i32.const 52)))

  ;; Frame record on TSP (48 bytes): saved_vsp, saved_special, saved_root_head, saved_csp, depth, unused, noise[6]
  ;; Root record on TSP (16 bytes): previous_head, count, slot0, slot1
  (func $push_frame (param $depth i32) (result i32) (local $frame i32) (local $root i32)
    (local.set $frame (i32.sub (call $ld (i32.const 4)) (i32.const 48)))
    (i32.store (local.get $frame) (call $ld (i32.const 0)))
    (i32.store offset=4 (local.get $frame) (call $ld (i32.const 12)))
    (i32.store offset=8 (local.get $frame) (call $ld (i32.const 16)))
    (i32.store offset=12 (local.get $frame) (call $ld (i32.const 8)))
    (i32.store offset=16 (local.get $frame) (local.get $depth))
    (local.set $root (i32.sub (local.get $frame) (i32.const 16)))
    (i32.store (local.get $root) (call $ld (i32.const 16)))
    (i32.store offset=4 (local.get $root) (i32.const 2))
    (i32.store offset=8 (local.get $root) (i32.add (i32.const 129) (i32.mul (local.get $depth) (i32.const 8))))
    (i32.store offset=12 (local.get $root) (i32.const 65))
    (call $st (i32.const 16) (local.get $root))
    (call $st (i32.const 4) (local.get $root))
    ;; bind the dynamic cell to 100 + depth and reserve 8 bytes of VSP scratch
    (call $st (i32.const 12) (i32.add (i32.const 100) (local.get $depth)))
    (call $st (i32.const 0) (i32.add (call $ld (i32.const 0)) (i32.const 8)))
    (call $event (i32.add (i32.const 100) (local.get $depth)))
    (local.get $frame))
  (func $push_cleanup (param $frame i32) (local $csp i32)
    (local.set $csp (i32.sub (call $ld (i32.const 8)) (i32.const 8)))
    (i32.store (local.get $csp) (i32.const 1))
    (i32.store offset=4 (local.get $csp) (local.get $frame))
    (call $st (i32.const 8) (local.get $csp)))
  ;; Ordinary and exceptional exits share one restoration path.
  (func $pop_frame (param $frame i32)
    (call $st (i32.const 12) (i32.load offset=4 (local.get $frame)))
    (call $st (i32.const 16) (i32.load offset=8 (local.get $frame)))
    (call $st (i32.const 8) (i32.load offset=12 (local.get $frame)))
    (call $st (i32.const 0) (i32.load (local.get $frame)))
    (call $st (i32.const 4) (i32.add (local.get $frame) (i32.const 48)))
    (call $event (i32.add (i32.const 300) (i32.load offset=16 (local.get $frame)))))
  ;; Unwind to a frame: every inner frame has departed, so the dynamic state
  ;; becomes this frame's own state as of its push (its binding, its root
  ;; record as head, its TSP, its VSP reserve and its cleanup record) before
  ;; its cleanup or handler code runs. Ordinary return reaches the same state
  ;; through the inner frames' own pops.
  (func $unwind_to (param $frame i32)
    (call $st (i32.const 12) (i32.add (i32.const 100) (i32.load offset=16 (local.get $frame))))
    (call $st (i32.const 16) (i32.sub (local.get $frame) (i32.const 16)))
    (call $st (i32.const 4) (i32.sub (local.get $frame) (i32.const 16)))
    (call $st (i32.const 0) (i32.add (i32.load (local.get $frame)) (i32.const 8)))
    (call $st (i32.const 8) (i32.sub (i32.load offset=12 (local.get $frame)) (i32.const 8))))
  ;; Cleanup: runs once per frame on either exit path, produces its own six
  ;; values in the frame's region, and records the dynamic state it observes
  ;; on entry (binding, root head, TSP, its frame, VSP, CSP, saved VSP and
  ;; saved CSP) in the cleanup-witness region for the oracle.
  (func $cleanup (param $frame i32) (local $i i32) (local $w i32)
    (local.set $w (i32.add (i32.const 30000) (i32.mul (i32.load offset=16 (local.get $frame)) (i32.const 32))))
    (i32.store (local.get $w) (call $ld (i32.const 12)))
    (i32.store offset=4 (local.get $w) (call $ld (i32.const 16)))
    (i32.store offset=8 (local.get $w) (call $ld (i32.const 4)))
    (i32.store offset=12 (local.get $w) (local.get $frame))
    (i32.store offset=16 (local.get $w) (call $ld (i32.const 0)))
    (i32.store offset=20 (local.get $w) (call $ld (i32.const 8)))
    (i32.store offset=24 (local.get $w) (i32.load (local.get $frame)))
    (i32.store offset=28 (local.get $w) (i32.load offset=12 (local.get $frame)))
    (call $bump (i32.const 24))
    (call $event (i32.add (i32.const 200) (i32.load offset=16 (local.get $frame))))
    (loop $l
      (i32.store (i32.add (i32.add (local.get $frame) (i32.const 24)) (i32.mul (local.get $i) (i32.const 4))) (i32.add (i32.const 1000) (local.get $i)))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br_if $l (i32.lt_u (local.get $i) (i32.const 6)))))
  (func $effect (param $depth i32) (call $bump (i32.const 28)) (call $event (i32.add (i32.const 400) (local.get $depth))))
  ;; Place N values in transit and raise the Lisp exit.
  (func $exit_with_values (param $n i32) (call $exit_with (local.get $n) (i32.const 0)))
  (func $exit_with (param $n i32) (param $noise i32) (local $i i32) (local $base i32)
    (local.set $base (call $ld (i32.const 40)))
    (block $done (loop $l
      (br_if $done (i32.ge_u (local.get $i) (local.get $n)))
      (i32.store (i32.add (local.get $base) (i32.mul (local.get $i) (i32.const 4)))
                 (if (result i32) (local.get $noise) (then (i32.add (i32.const 2000) (local.get $i))) (else (call $value (local.get $i)))))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $l)))
    (call $st (i32.const 44) (local.get $n))
    (call $event (i32.const 50))
    (throw $lisp (local.get $n)))
  (func $value (param $i i32) (result i32)
    (block $b (result i32)
      (i32.const 4) (br_if $b (i32.eqz (local.get $i))) (drop)
      (i32.const -28) (br_if $b (i32.eq (local.get $i) (i32.const 1))) (drop)
      (i32.const 44) (br_if $b (i32.eq (local.get $i) (i32.const 2))) (drop)
      (i32.const 129) (br_if $b (i32.eq (local.get $i) (i32.const 3))) (drop)
      (i32.const 0) (br_if $b (i32.eq (local.get $i) (i32.const 4))) (drop)
      (i32.const 2147483644)))
  ;; Copy the transit region into the caller-owned result region and return the pair.
  (func $deliver_transit (result i32 i32) (local $i i32) (local $n i32)
    (local.set $n (call $ld (i32.const 44)))
    (block $done (loop $l
      (br_if $done (i32.ge_u (local.get $i) (local.get $n)))
      (i32.store (i32.add (call $ld (i32.const 32)) (i32.mul (local.get $i) (i32.const 4)))
                 (i32.load (i32.add (call $ld (i32.const 40)) (i32.mul (local.get $i) (i32.const 4)))))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $l)))
    (call $st (i32.const 36) (local.get $n))
    (if (result i32) (i32.eqz (local.get $n)) (then (i32.const 65)) (else (i32.load (call $ld (i32.const 32)))))
    (local.get $n))
  (func $arg (param $i i32) (result i32) (i32.load (i32.add (i32.const 4096) (i32.mul (local.get $i) (i32.const 4)))))

  ;; Recoverable check: signal the condition to the installed handler without
  ;; unwinding; the handler may transfer a replacement to the restart point.
  (func $use_value_handler (param $condition i32)
    (call $bump (i32.const 48)) (call $event (i32.const 61))
    (throw $use_value (i32.const 8)))
  (func $declining_handler (param $condition i32)
    (call $bump (i32.const 48)) (call $event (i32.const 62)))
  (func $check_even (param $x i32) (param $handler i32) (result i32)
    (if (i32.eqz (i32.and (local.get $x) (i32.const 1))) (then (return (local.get $x))))
    (block $restart (result i32)
      (try_table (catch $use_value $restart)
        (call_indirect (type $handler) (local.get $x) (local.get $handler))
        ;; the handler declined: the check becomes an error with one value
        (call $exit_with_values (i32.const 1)))
      (unreachable))
    (call $st (i32.const 60) (i32.const 1)) (call $event (i32.const 70)))

  ;; Depth 4: the innermost Lisp frame; selects the case from argument 0.
  (func $f4 (param $self i32) (param $nargs i32) (result i32 i32) (local $frame i32) (local $mode i32) (local $x i32)
    (local.set $frame (call $push_frame (i32.const 4)))
    (local.set $mode (call $arg (i32.const 0)))
    (if (i32.eqz (local.get $mode)) (then (local.set $x (call $arg (i32.const 1)))))
    (if (i32.eq (local.get $mode) (i32.const 1)) (then (call $exit_with_values (call $arg (i32.const 1)))))
    (if (i32.eq (local.get $mode) (i32.const 2)) (then (call $exit_with_values (i32.const 6))))
    (if (i32.eq (local.get $mode) (i32.const 3)) (then (call $event (i32.const 53)) (throw $unhandled (i32.const 77))))
    (if (i32.eq (local.get $mode) (i32.const 5)) (then (call $exit_with_values (i32.const 6))))
    (if (i32.eq (local.get $mode) (i32.const 6)) (then (call $exit_with_values (i32.const 6))))
    (if (i32.eq (local.get $mode) (i32.const 4)) (then (local.set $x (call $check_even (call $arg (i32.const 1)) (i32.const 0)))))
    (if (i32.eq (local.get $mode) (i32.const 7)) (then (local.set $x (call $check_even (call $arg (i32.const 1)) (i32.const 1)))))
    ;; ordinary path: two values derived from the (possibly replaced) argument
    (i32.store (call $ld (i32.const 32)) (i32.mul (local.get $x) (i32.const 3)))
    (i32.store offset=4 (call $ld (i32.const 32)) (i32.add (local.get $x) (call $ld (i32.const 12))))
    (call $st (i32.const 36) (i32.const 2))
    (call $effect (i32.const 4))
    (call $pop_frame (local.get $frame))
    (i32.load (call $ld (i32.const 32))) (i32.const 2))

  ;; Depth 3 and 2: frames with cleanup. Depth 3's cleanup raises a second
  ;; exit in mode 2; depth 2's cleanup always completes.
  (func $f3 (param $self i32) (param $nargs i32) (result i32 i32) (local $frame i32) (local $e exnref) (local $v0 i32) (local $n i32)
    (local.set $frame (call $push_frame (i32.const 3)))
    (call $push_cleanup (local.get $frame))
    (block $h (result exnref)
      (try_table (result i32 i32) (catch_all_ref $h) (call $f4 (local.get $self) (local.get $nargs)))
      (local.set $n) (local.set $v0)
      (call $effect (i32.const 3))
      (call $cleanup (local.get $frame))
      (call $pop_frame (local.get $frame))
      (return (local.get $v0) (local.get $n)))
    (local.set $e)
    (call $unwind_to (local.get $frame))
    (call $cleanup (local.get $frame))
    (call $pop_frame (local.get $frame))
    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2)) (then (call $event (i32.const 52)) (throw $other (i32.const 9))))
    (throw_ref (local.get $e)))
  (func $f2 (param $self i32) (param $nargs i32) (result i32 i32) (local $frame i32) (local $e exnref) (local $v0 i32) (local $n i32)
    (local.set $frame (call $push_frame (i32.const 2)))
    (call $push_cleanup (local.get $frame))
    (block $h (result exnref)
      (try_table (result i32 i32) (catch_all_ref $h)
        (if (result i32 i32) (i32.eq (call $arg (i32.const 0)) (i32.const 6))
          (then (call $deep (i32.const 5)))
          (else (call $f3 (local.get $self) (local.get $nargs)))))
      (local.set $n) (local.set $v0)
      (call $effect (i32.const 2))
      (call $cleanup (local.get $frame))
      (call $pop_frame (local.get $frame))
      (return (local.get $v0) (local.get $n)))
    (local.set $e)
    (call $unwind_to (local.get $frame))
    (call $cleanup (local.get $frame))
    (call $pop_frame (local.get $frame))
    (throw_ref (local.get $e)))
  ;; Mode 6: a long chain of cleanup frames, depths 5 through 12.
  (func $deep (param $depth i32) (result i32 i32) (local $frame i32) (local $e exnref)
    (local.set $frame (call $push_frame (local.get $depth)))
    (call $push_cleanup (local.get $frame))
    (block $h (result exnref)
      (try_table (result i32 i32) (catch_all_ref $h)
        (if (result i32 i32) (i32.lt_u (local.get $depth) (i32.const 12))
          (then (call $deep (i32.add (local.get $depth) (i32.const 1))))
          (else (call $exit_with_values (i32.const 6)) (unreachable))))
      (drop) (drop) (unreachable))
    (local.set $e)
    (call $unwind_to (local.get $frame))
    (call $cleanup (local.get $frame))
    (call $pop_frame (local.get $frame))
    (throw_ref (local.get $e)))

  ;; The nested debugger: invoked from inside the outer handler while the
  ;; caught values are already secured in the caller-owned region.
  (func $debugger (local $frame i32) (local $e exnref)
    (call $event (i32.const 80))
    (local.set $frame (call $push_frame (i32.const 9)))
    (call $push_cleanup (local.get $frame))
    (call $bump (i32.const 20))
    (if (i32.gt_u (call $ld (i32.const 20)) (call $ld (i32.const 56))) (then (call $st (i32.const 56) (call $ld (i32.const 20)))))
    (block $h (result exnref)
      (try_table (catch_all_ref $h) (call $exit_with (i32.const 3) (i32.const 1)))
      (unreachable))
    (local.set $e)
    (call $unwind_to (local.get $frame))
    (call $cleanup (local.get $frame))
    (call $pop_frame (local.get $frame))
    (call $st (i32.const 20) (i32.sub (call $ld (i32.const 20)) (i32.const 1)))
    (block $done (result i32)
      (try_table (catch $lisp $done) (throw_ref (local.get $e)))
      (unreachable))
    (drop)
    (call $event (i32.const 81)))

  ;; Depth 1: the handler frame. Catches $lisp and $other; $unhandled passes
  ;; through to the export adapter and then to the host.
  (func $outer (param $self i32) (param $nargs i32) (result i32 i32) (local $frame i32) (local $v0 i32) (local $n i32) (local $payload i32) (local $e exnref)
    (local.set $frame (call $push_frame (i32.const 1)))
    (call $bump (i32.const 20))
    (if (i32.gt_u (call $ld (i32.const 20)) (call $ld (i32.const 56))) (then (call $st (i32.const 56) (call $ld (i32.const 20)))))
    (block $any (result exnref) (try_table (catch_all_ref $any)
    (block $lisp_h (result i32)
      (block $other_h (result i32)
        (try_table (result i32 i32) (catch $lisp $lisp_h) (catch $other $other_h) (call $f2 (local.get $self) (local.get $nargs)))
        (local.set $n) (local.set $v0)
        (call $st (i32.const 20) (i32.sub (call $ld (i32.const 20)) (i32.const 1)))
        (call $pop_frame (local.get $frame))
        (return (local.get $v0) (local.get $n)))
      ;; $other: one value, the cleanup's payload
      (local.set $payload)
      (call $unwind_to (local.get $frame))
      (call $event (i32.const 64))
      (i32.store (call $ld (i32.const 32)) (local.get $payload))
      (call $st (i32.const 36) (i32.const 1))
      (call $st (i32.const 20) (i32.sub (call $ld (i32.const 20)) (i32.const 1)))
      (call $pop_frame (local.get $frame))
      (return (local.get $payload) (i32.const 1)))
    (local.set $payload)
    (call $unwind_to (local.get $frame))
    (call $event (i32.const 63))
    (call $deliver_transit) (local.set $n) (local.set $v0)
    (if (i32.eq (call $arg (i32.const 0)) (i32.const 5)) (then (call $debugger)))
    (call $st (i32.const 20) (i32.sub (call $ld (i32.const 20)) (i32.const 1)))
    (call $pop_frame (local.get $frame))
    (return (local.get $v0) (local.get $n)))
    (unreachable))
    (local.set $e)
    (call $unwind_to (local.get $frame))
    (call $st (i32.const 20) (i32.sub (call $ld (i32.const 20)) (i32.const 1)))
    (call $pop_frame (local.get $frame))
    (throw_ref (local.get $e)))

  ;; Export adapter: an unhandled exception leaves every frame restored and
  ;; reaches the host as the same exception object.
  (func (export "entry") (param $self i32) (param $nargs i32) (result i32 i32) (local $e exnref)
    (block $h (result exnref)
      (try_table (result i32 i32) (catch_all_ref $h) (call $outer (local.get $self) (local.get $nargs)))
      (return))
    (local.set $e)
    (call $event (i32.const 90))
    (throw_ref (local.get $e))))
