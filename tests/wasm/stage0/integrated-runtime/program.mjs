// Hand-emitted Lisp-like frames. The C stack stays live while suspend_request waits.
export function programWat(schema, slot, { staleWasmRoot = false, omitExceptionPark = false } = {}) {
  const f=schema.tcr;
  const fields=['root_head','binding_depth','vsp','tsp','csp','binding_cookie','handler_cookie','active_request'];
  return `(module
    (import "env" "memory" (memory 8 16 shared))
    (import "env" "table" (table ${slot+1} funcref))
    (import "kernel" "__stack_pointer" (global $sp (mut i32)))
    (import "kernel" "get_tcr" (func $tcr (result i32)))
    (import "kernel" "admit" (func $admit))
    (import "kernel" "park" (func $park))
    (import "kernel" "root_value" (func $root (result i32)))
    (import "kernel" "car_value" (func $car (param i32) (result i32)))
    (import "kernel" "suspend_request" (func $suspend (param i32 i32 i32) (result i32)))
    (import "emitted" "exit" (tag $exit (param i32)))
    (type $entry (func (param i32) (result i32)))
    (func $inner (param $opcode i32) (param $index i32) (result i32)
      (local $cached i32) (local $raw i32)
      (local.set $cached (call $root))
      (drop (call $suspend (local.get $opcode) (local.get $index) (local.get $cached)))
      ${staleWasmRoot ? '' : '(local.set $cached (call $root))'}
      (local.set $raw (i32.sub (local.get $cached) (i32.const 1)))
      (drop (call $car (local.get $cached)))
      (i32.store offset=${f.observed_raw} (call $tcr) (local.get $raw))
      (local.get $cached))
    (func $middle (param $opcode i32) (result i32)
      (local $binding i32) (local $result i32) (local $oldVsp i32) (local $frame i32)
      (local.set $binding (i32.load offset=${f.binding_cookie} (call $tcr)))
      (local.set $oldVsp (i32.load offset=${f.vsp} (call $tcr)))
      (local.set $frame (i32.add (local.get $oldVsp) (i32.const 32)))
      (i32.store (local.get $frame) (i32.load offset=${f.root_head} (call $tcr)))
      (i32.store offset=4 (local.get $frame) (i32.const 2))
      (i32.store offset=8 (local.get $frame) (call $root))
      (i32.store offset=12 (local.get $frame) (call $root))
      (i32.store offset=${f.root_head} (call $tcr) (local.get $frame))
      (i32.store offset=${f.vsp} (call $tcr) (i32.add (local.get $oldVsp) (i32.const 80)))
      (i32.store offset=${f.binding_depth} (call $tcr)
        (i32.add (i32.load offset=${f.binding_depth} (call $tcr)) (i32.const 1)))
      (i32.store offset=${f.binding_cookie} (call $tcr) (i32.const 287454020))
      (local.set $result (call $inner (local.get $opcode) (i32.const 0)))
      (if (i32.ne (i32.const 287454020) (i32.load offset=${f.binding_cookie} (call $tcr))) (then (unreachable)))
      (if (i32.ne (i32.load offset=8 (local.get $frame)) (call $root)) (then (unreachable)))
      (i32.store offset=${f.binding_cookie} (call $tcr) (local.get $binding))
      (i32.store offset=${f.binding_depth} (call $tcr)
        (i32.sub (i32.load offset=${f.binding_depth} (call $tcr)) (i32.const 1)))
      (i32.store offset=${f.root_head} (call $tcr) (i32.load (local.get $frame)))
      (i32.store offset=${f.vsp} (call $tcr) (local.get $oldVsp))
      (local.get $result))
    (func (export "debugger")
      (drop (call $inner (i32.const 3) (i32.const 1))))
    (func (export "outer") (param $opcode i32) (param $count i32) (result i32 i32)
      (local $thread i32) (local $beforeSp i32) (local $root i32) (local $caught i32)
      (local $continuation i32) (local $value0 i32) ${fields.map((_,i)=>`(local $saved${i} i32)`).join(' ')}
      (call $admit)
      (local.set $thread (call $tcr))
      (local.set $beforeSp (global.get $sp))
      (local.set $continuation (i32.load offset=${f.continuation} (local.get $thread)))
      ${fields.map((name,i)=>`(local.set $saved${i} (i32.${name==='active_request'?'atomic.load':'load'} offset=${f[name]} (local.get $thread)))`).join('\n')}
      (i32.store offset=${f.handler_cookie} (local.get $thread) (i32.const 1432778632))
      (i32.store offset=${f.nvalues} (local.get $thread) (local.get $count))
      (local.set $caught
        (block $catch (result i32)
          (try_table (catch $exit $catch)
            (local.set $root (call $middle (local.get $opcode))))
          (i32.const 0)))
      (global.set $sp (local.get $beforeSp))
      ${fields.map((name,i)=>`(i32.${name==='active_request'?'atomic.store':'store'} offset=${f[name]} (local.get $thread) (local.get $saved${i}))`).join('\n')}
      (if (local.get $caught)
        (then
          (i32.store offset=${f.cleanup} (local.get $thread)
            (i32.add (i32.load offset=${f.cleanup} (local.get $thread)) (i32.const 1)))
          ${omitExceptionPark ? '' : '(call $park)'}
          (return (i32.const -1) (local.get $count))))
      (if (i32.ne (local.get $continuation) (i32.load offset=${f.continuation} (local.get $thread))) (then (unreachable)))
      (if (i32.eq (local.get $opcode) (i32.const 2))
        (then
          (i32.store offset=${f.progress} (local.get $thread)
            (call_indirect (type $entry) (local.get $root) (i32.const ${slot})))))
      (local.set $value0 (if (result i32) (i32.eqz (local.get $count))
        (then (i32.const 65))
        (else (i32.load (i32.load offset=${f.mv_base} (local.get $thread))))))
      (call $park)
      (local.get $value0)
      (local.get $count)))`;
}

export const lazyWat = `(module
  (import "env" "memory" (memory 8 16 shared))
  (func (export "entry") (param $root i32) (result i32)
    (i32.add (i32.load offset=3 (local.get $root)) (i32.const 68))))`;
