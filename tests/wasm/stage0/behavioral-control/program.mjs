// Hand-built escaping environment and B-shaped call entry; no CCL image layout claim.
export function program(mode='normal') {
  if(!['normal','drop-extra','remove-capture','skip-cleanup','skip-unwind-cleanup','reverse-cleanup'].includes(mode))throw Error('unknown mutation');
  const inner=mode==='reverse-cleanup'?3:2,outer=mode==='reverse-cleanup'?2:3;
  return `(module
    (import "host" "escape" (tag $escape (param i32)))
    (memory (export "memory") 1 1)
    (table (export "table") 1 funcref)
    (type $B (func (param i32 i32) (result i32 i32)))
    (global $next (mut i32) (i32.const 512))
    (global $nvalues (export "nvalues") (mut i32) (i32.const 0))
    (global $logn (export "log_count") (mut i32) (i32.const 0))
    (global $effects (export "cleanup_effect") (mut i32) (i32.const 0))
    (global $active (export "factory_active") (mut i32) (i32.const 0))
    ;; Setup factory returns a descriptor after its frame has returned. Each
    ;; descriptor owns a distinct environment: value, calls, initial value.
    (func (export "make") (param $initial i32) (result i32) (local $self i32)
      (global.set $active (i32.const 1))
      (local.set $self (global.get $next))
      (global.set $next (i32.add (local.get $self) (i32.const 32)))
      (i32.store (local.get $self) (i32.const 0))
      (i32.store offset=4 (local.get $self) (i32.add (local.get $self) (i32.const 8)))
      (i32.store offset=8 (local.get $self) (i32.shl (local.get $initial) (i32.const 2)))
      (i32.store offset=12 (local.get $self) (i32.const 0))
      (i32.store offset=16 (local.get $self) (i32.shl (local.get $initial) (i32.const 2)))
      (global.set $active (i32.const 0)) (local.get $self))
    (func $mark (param $value i32)
      (i32.store (i32.add (i32.const 192) (i32.shl (global.get $logn) (i32.const 2))) (local.get $value))
      (global.set $logn (i32.add (global.get $logn) (i32.const 1))))
    (func $cleanup (param $value i32)
      (call $mark (local.get $value))
      (global.set $effects (i32.add (i32.mul (global.get $effects) (i32.const 10)) (local.get $value))))
    ;; B entry: self/count parameters, arguments at 128, two Wasm results and
    ;; caller-owned extra-value area at 64. Tagged integer words use D1 shift 2.
    (func $closure (type $B) (param $self i32) (param $nargs i32) (result i32 i32)
      (local $env i32) (local $old i32) (local $new i32) (local $delta i32) (local $calls i32)
      (if (i32.ne (local.get $nargs) (i32.const 2)) (then unreachable))
      (global.set $nvalues (i32.const 0)) (global.set $logn (i32.const 0)) (global.set $effects (i32.const 0))
      (call $mark (i32.const 1))
      (local.set $env (i32.load offset=4 (local.get $self)))
      (local.set $old (i32.load offset=${mode==='remove-capture'?8:0} (local.get $env)))
      (local.set $delta (i32.load (i32.const 128)))
      (local.set $new (i32.add (local.get $old) (local.get $delta)))
      (local.set $calls (i32.add (i32.load offset=4 (local.get $env)) (i32.const 1)))
      (i32.store (local.get $env) (local.get $new))
      (i32.store offset=4 (local.get $env) (local.get $calls))
      (try
        (do
          (try
            (do
              (if (i32.load (i32.const 132))
                (then (throw $escape (i32.add (i32.const 700) (i32.shr_s (local.get $new) (i32.const 2)))))))
            (catch $escape drop ${['skip-cleanup','skip-unwind-cleanup'].includes(mode)?'':`(call $cleanup (i32.const ${inner}))`} rethrow 0))
          ${mode==='skip-cleanup'?'':`(call $cleanup (i32.const ${inner}))`})
        (catch $escape drop (call $cleanup (i32.const ${outer})) rethrow 0))
      (call $cleanup (i32.const ${outer}))
      (i32.store (i32.const 64) (local.get $new))
      (i32.store (i32.const 68) (local.get $old))
      (i32.store (i32.const 72) (local.get $delta))
      (i32.store (i32.const 76) (i32.load offset=8 (local.get $env)))
      ${mode==='drop-extra'?'':`(i32.store (i32.const 80) (i32.shl (local.get $calls) (i32.const 2)))`}
      (i32.store (i32.const 84) (i32.const 292))
      (global.set $nvalues (i32.const 6))
      (local.get $new) (i32.const 6))
    (elem (i32.const 0) $closure)
    (func (export "invoke") (param $self i32) (param $nargs i32) (result i32 i32)
      (call_indirect (type $B) (local.get $self) (local.get $nargs) (i32.load (local.get $self)))))`;
}
