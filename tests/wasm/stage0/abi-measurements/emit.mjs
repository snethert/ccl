import {imports, functionWat} from './functions.mjs';

export function registryWat(slots) {
  return `(module (import "guard" "fail" (func $fail))
    (func (export "lookup") (param $code i32) (param $role i32) (result i32)
      (if (i32.gt_u (local.get $role) (i32.const 2)) (then (call $fail)))
      ${slots.entries.map(e=>`(if (i32.eq (local.get $code) (i32.const ${e.code})) (then
        (return (i32.add (i32.const ${e.G}) (local.get $role)))))`).join('\n')}
      (call $fail) (unreachable)))`;
}

/* The identical runtime still emits every schedule point. The measured mode
   handles those points in Wasm; diagnostic mode forwards them to the host. */
export function scheduleWat() {
  return `(module (import "host" "point" (func $host (param i32 i32 i32)))
    (global $quiet (mut i32) (i32.const 0))
    (global $events (export "events") (mut i32) (i32.const 0))
    (func (export "quiet") (param i32) (global.set $quiet (local.get 0)))
    (func (export "point") (param i32 i32 i32)
      (global.set $events (i32.add (global.get $events) (i32.const 1)))
      (if (i32.eqz (global.get $quiet)) (then (call $host (local.get 0) (local.get 1) (local.get 2))))))`;
}

function driverBody(runtime,schema,k,slots,packaging,mut) {
  const f={...runtime.tcr,...schema.tcr}, s=schema.state;
  const t=n=>`(i32.load offset=${f[n]} (call $tcr))`;
  const st=n=>`(i32.load offset=${s[n]} (call $state))`;
  const params=`(param $self i32) (param $n i32) ${Array.from({length:k},(_,i)=>`(param $a${i} i32)`).join(' ')}`;
  const args=`(local.get $self) (local.get $n) ${Array.from({length:k},(_,i)=>`(local.get $a${i})`).join(' ')}`;
  return `
    (import "abi" "start" (func $start (param i32 i32 i32) (result i32 i32)))
    (import "abi" "measurement_mode" (func $mode (param i32)))
    (import "kernel" "admit" (func $admit)) (import "kernel" "park" (func $park))
    (import "kernel" "measure_ownership" (func $ownership))
    (import "kernel" "measure_digest" (func $digest (param i32) (result i32)))
    (global $indirect (mut i32) (i32.const 0))
    (func (export "dispatch") ${params} (result i32 i32)
      (local $code i32) (local.set $code (i32.shr_u (call $car (local.get $self)) (i32.const 2)))
      ${packaging==='direct'?`(if (i32.eqz (global.get $indirect)) (then
        ${slots.entries.map(e=>`(if (i32.eq (local.get $code) (i32.const ${e.code})) (then (return_call $entry${e.code} ${args})))`).join('\n')}
        (unreachable)))`:''}
      (return_call_indirect (type $G) ${args} (call $lookup (local.get $code) (i32.const 0))))
    (func $input_address (param $i i32) (result i32)
      (i32.add ${st('input')} (i32.add (i32.const 8)
        (i32.add (i32.mul (i32.div_u (local.get $i) (i32.const 8)) (i32.const 40))
                 (i32.mul (i32.rem_u (local.get $i) (i32.const 8)) (i32.const 4))))))
    (func $mix (param $h i32) (param $v i32) (result i32)
      (i32.mul (i32.xor (local.get $h) (local.get $v)) (i32.const 16777619)))
    (func (export "batch") (param $iterations i32) (param $offset i32) (result i32 i32)
      (local $i i32) (local $j i32) (local $record i32) (local $prefix i32) (local $total i32)
      (local $v i32) (local $n i32) (local $h i32) (local $one i32)
      (if (i32.or (i32.eqz (local.get $iterations)) (i32.gt_u (local.get $iterations) (i32.const 4096))) (then (unreachable)))
      (call $admit) (call $ownership) (call $mode (i32.const 1))
      (local.set $h (i32.const -2128831035))
      (loop $batch
        (local.set $record (i32.add (i32.load offset=72 (call $state))
          (i32.mul (i32.and (i32.add (local.get $i) (local.get $offset)) (i32.const 31)) (i32.const 256))))
        (i32.store offset=${f.nvalues} (call $tcr) (i32.const 0))
        (local.set $j (i32.const 0))
        (loop $clear_output
          (i32.store (i32.add ${st('output')} (i32.mul (local.get $j) (i32.const 4))) (i32.const 65))
          (local.set $j (i32.add (local.get $j) (i32.const 1)))
          (br_if $clear_output (i32.lt_u (local.get $j) (i32.const 6))))
        (local.set $j (i32.const 0))
        (loop $inputs
          (i32.store (call $input_address (local.get $j))
            (i32.load (i32.add (local.get $record) (i32.add (i32.const 32) (i32.mul (local.get $j) (i32.const 4))))))
          (local.set $j (i32.add (local.get $j) (i32.const 1)))
          (br_if $inputs (i32.lt_u (local.get $j) (i32.const 32))))
        (i32.store offset=${s.value_count} (call $state) (i32.load offset=8 (local.get $record)))
        (i32.store offset=${s.suspend} (call $state) (i32.load offset=12 (local.get $record)))
        (global.set $indirect (i32.load offset=24 (local.get $record)))
        (i32.store offset=76 (call $state) (i32.load offset=28 (local.get $record)))
        (if (i32.load offset=20 (local.get $record)) (then
          (i32.store (call $input_address (i32.const 0)) (call $cons (call $input (i32.const 0)) (i32.const 65)))))
        (local.set $prefix (i32.load offset=4 (local.get $record)))
        (local.set $total (i32.load offset=16 (local.get $record)))
        (if (local.get $total) (then
          (i32.store (call $input_address (i32.const 31)) (i32.const 65))
          (local.set $j (local.get $total))
          (loop $list
            (local.set $j (i32.sub (local.get $j) (i32.const 1)))
            (i32.store (call $input_address (i32.const 31))
              (call $cons (i32.load (i32.add (local.get $record) (i32.add (i32.const 32) (i32.mul (local.get $j) (i32.const 4))))) (call $input (i32.const 31))))
            (br_if $list (i32.gt_u (local.get $j) (local.get $prefix))))))
        (call $start (i32.load (local.get $record)) (local.get $prefix)
          (if (result i32) (local.get $total) (then (i32.const 4)) (else (i32.const 0))))
        (local.set $n) (local.set $v)
        (if ${st('error')} (then (unreachable)))
        (local.set $one (call $mix (i32.const -2128831035) (local.get $n)))
        (local.set $one (call $mix (local.get $one) (call $digest (local.get $v))))
        (local.set $j (i32.const 0))
        (block $consumed (loop $values
          (br_if $consumed (i32.ge_u (local.get $j) (local.get $n)))
          ${mut.ignoreResult?'':`(local.set $one (call $mix (local.get $one) (call $digest
            (i32.load (i32.add ${st('output')} (i32.mul (local.get $j) (i32.const 4)))))))`}
          (local.set $j (i32.add (local.get $j) (i32.const 1))) (br $values)))
        (local.set $h (call $mix (local.get $h) (local.get $one)))
        (call $poll)
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br_if $batch (i32.lt_u (local.get $i) (local.get $iterations))))
      (call $mode (i32.const 0)) (call $ownership) (call $park)
      (local.get $h) (local.get $i))`;
}

export function driverWat(runtime,schema,k,slots,packaging,mut={}) {
  return `(module ${imports(k,slots.minimum)} ${driverBody(runtime,schema,k,slots,packaging,mut)})`;
}

export function bundleWat(runtime,schema,k,slots,packaging,mut={}) {
  const prefix=`(module ${imports(k,slots.minimum)}`;
  const bodies=slots.entries.map(e=>{
    const text=functionWat(runtime,schema,k,slots,e,mut);
    if (!text.startsWith(prefix)) throw Error('unexpected callable module boundary');
    return text.slice(prefix.length,-1)
      .replace('(func $G (export "G")',`(func $entry${e.code} (export "G${e.code}")`)
      .replaceAll('(call $G ',`(call $entry${e.code} `)
      .replaceAll('(return_call $G ',`(return_call $entry${e.code} `)
      .replace('(export "direct")',`(export "direct${e.code}")`)
      .replace('(export "adapter")',`(export "adapter${e.code}")`);
  });
  return `${prefix} ${driverBody(runtime,schema,k,slots,packaging,mut)} ${bodies.join('\n')})`;
}
