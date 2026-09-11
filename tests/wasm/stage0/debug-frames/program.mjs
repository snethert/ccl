// Emitted frame construction is independent of the C reader's structure layout.
export function programWat(runtime, schema, {wrongVersion=false,wrongSite=false,omitRestore=false}={}) {
  const f={...runtime.tcr,...schema.tcr}, h=schema.header, p=schema.payload;
  const load=(name)=>`(i32.load offset=${f[name]} (call $tcr))`;
  const store=(off,v)=>`(i32.store offset=${off} (local.get $frame) ${v})`;
  const saves={saved_vsp:'vsp',saved_tsp:'tsp',saved_csp:'csp',saved_binding_depth:'binding_depth',
    saved_handler_cookie:'handler_cookie',saved_binding_cookie:'binding_cookie',saved_mv_base:'mv_base',
    saved_mv_owner_top:'mv_owner_top',saved_active_request:'active_request'};
  return `(module
    (import "env" "memory" (memory 8 16 shared))
    (import "kernel" "get_tcr" (func $tcr (result i32)))
    (import "kernel" "__stack_pointer" (global $sp (mut i32)))
    (import "kernel" "admit" (func $admit))
    (import "kernel" "park" (func $park))
    (import "kernel" "root_value" (func $root (result i32)))
    (import "kernel" "car_value" (func $car (param i32) (result i32)))
    (import "kernel" "suspend_request" (func $suspend (param i32 i32 i32) (result i32)))
    (import "kernel" "debug_reserve" (func $reserve (result i32)))
    (import "kernel" "debug_commit" (func $commit (param i32)))
    (import "kernel" "debug_pop" (func $pop))
    (import "kernel" "debug_unwind" (func $unwind (param i32)))
    (import "kernel" "debug_site" (func $site (param i32)))
    (import "kernel" "debug_inspect" (func $inspect (param i32)))
    (import "kernel" "debug_live_handle_reply" (func $live_handle))
    (import "kernel" "debug_handle_reply" (func $handle (param i32 i32 i32)))
    (import "emitted" "exit" (tag $exit (param i32)))
    (import "emitted" "raise" (func $raise (param i32)))
    (global $policy (mut i32) (i32.const 3))
    (global $throwNested (mut i32) (i32.const 0))
    (global $oldAddress (mut i32) (i32.const 0))
    (global $oldGeneration (mut i32) (i32.const 0))
    (global $oldLifetime (mut i32) (i32.const 0))
    (func (export "set_handle") (param $address i32) (param $generation i32) (param $lifetime i32)
      (global.set $oldAddress (local.get $address)) (global.set $oldGeneration (local.get $generation)) (global.set $oldLifetime (local.get $lifetime)))
    (func $enter (param $code i32) (param $version i32) (param $source i32)
                 (param $a i32) (param $b i32) (param $x i32) (result i32)
      (local $frame i32) (local $root i32)
      (local.set $frame (call $reserve))
      (local.set $root (call $root))
      ${store(h.layout_version,'(i32.const 1)')}
      ${store(h.frame_bytes,`(i32.const ${schema.frame_bytes})`)}
      ${store(h.previous_frame,load('frame_head'))}
      ${store(h.frame_generation,load('frame_serial'))}
      ${store(h.logical_code_id,'(i32.shl (local.get $code) (i32.const 2))')}
      ${store(h.code_version,wrongVersion?'(i32.const 3)':'(local.get $version)')}
      ${store(h.source_site_id,wrongSite?'(i32.const 9999)':'(local.get $source)')}
      ${store(h.policy_flags,'(global.get $policy)')}
      ${store(h.binding_checkpoint,load('tsp'))}
      ${store(h.handler_checkpoint,load('csp'))}
      ${store(h.root_descriptor,'(local.get $code)')}
      ${store(h.self_slot,`(i32.const ${p.self})`)}
      ${store(h.argument_count,'(i32.const 2)')}
      ${store(h.value_count,load('nvalues'))}
      ${store(h.mv_descriptor,`(i32.add (call $tcr) (i32.const ${f.nvalues}))`)}
      ${store(p.root_previous,load('root_head'))}
      ${store(p.root_count,'(i32.const 6)')}
      ${store(p.self,'(local.get $root)')}
      ${store(p.argument_a,'(local.get $a)')}
      ${store(p.argument_b,'(local.get $b)')}
      ${store(p.shadow_x,'(local.get $x)')}
      ${store(p.captured_cell,`(i32.load offset=4 ${load('root_slot')})`)}
      ${store(p.pending,'(local.get $root)')}
      ${store(p.raw_snapshot,'(local.get $root)')}
      ${store(p.unavailable_poison,'(i32.const -559038737)')}
      ${Object.entries(saves).map(([name,field])=>store(p[name],load(field))).join('\n')}
      ;; Actual binding and handler records occupy the existing owned TSP/CSP regions.
      (i32.store ${load('tsp')} (local.get $x))
      (i32.store ${load('csp')} (local.get $code))
      (i32.store offset=${f.tsp} (call $tcr) (i32.add ${load('tsp')} (i32.const 4)))
      (i32.store offset=${f.csp} (call $tcr) (i32.add ${load('csp')} (i32.const 4)))
      (i32.store offset=${f.vsp} (call $tcr) (i32.add ${load('vsp')} (i32.const 8)))
      (i32.store offset=${f.binding_depth} (call $tcr) (i32.add ${load('binding_depth')} (i32.const 1)))
      (i32.store offset=${f.binding_cookie} (call $tcr) (local.get $x))
      (i32.store offset=${f.handler_cookie} (call $tcr) (local.get $code))
      (call $commit (local.get $frame))
      (local.get $frame))
    (func $inner (param $a i32) (param $b i32)
      (local $frame i32)
      (local.set $frame (call $enter (i32.const 42) (i32.const 1) (i32.const 4201)
        (local.get $a) (local.get $b) (i32.const 888)))
      (call $inspect (i32.const 1))
      ;; @site 4201 inner host-suspension
      (drop (call $suspend (i32.const 1) (i32.const 0) (call $root)))
      (call $site (i32.const 4202))
      ;; Reload the GC-updated emitted slot, then derive its interior address in car.
      (drop (call $car (i32.load offset=${p.argument_b} (local.get $frame))))
      ;; @site 4202 inner resumed-inspection
      (call $inspect (i32.const 2))
      (call $pop))
    (func (export "debugger")
      (local $frame i32)
      (local.set $frame (call $enter (i32.const 43) (i32.const 1) (i32.const 4301)
        (i32.const -28) (call $root) (i32.const 1332)))
      (call $inspect (i32.const 3))
      ;; @site 4301 debugger nested-host-suspension
      (drop (call $suspend (i32.const 3) (i32.const 1) (call $root)))
      (call $site (i32.const 4302))
      (drop (call $car (i32.load offset=${p.captured_cell} (local.get $frame))))
      ;; @site 4302 debugger resumed-inspection
      (call $inspect (i32.const 4))
      (if (global.get $throwNested) (then (call $raise (call $tcr))))
      (call $pop))
    (func $run (param $count i32) (param $policy i32) (param $throw i32) (param $version i32)
               (result i32 i32)
      (local $beforeSp i32) (local $beforeHead i32) (local $frame i32) (local $caught i32) (local $value0 i32)
      (global.set $policy (local.get $policy)) (global.set $throwNested (local.get $throw))
      (call $admit)
      (local.set $beforeSp (global.get $sp)) (local.set $beforeHead ${load('frame_head')})
      (local.set $frame (call $enter (i32.const 41) (local.get $version)
        (if (result i32) (i32.eq (local.get $version) (i32.const 1)) (then (i32.const 4101)) (else (i32.const 4111)))
        (i32.const 44) (call $root) (i32.add (i32.const 440) (i32.shl (local.get $version) (i32.const 2)))))
      (call $live_handle)
      (if (global.get $oldAddress) (then (call $handle (global.get $oldAddress) (global.get $oldGeneration) (global.get $oldLifetime))))
      (local.set $caught
        (block $catch (result i32)
          (try_table (catch $exit $catch)
            ;; @site 4101,4111 run inner-call
            (call $inner (i32.const 44) (call $root)))
          (i32.const 0)))
      (if (local.get $caught)
        (then
          (global.set $sp (local.get $beforeSp))
          (call $unwind (local.get $beforeHead))
          (i32.store offset=${f.cleanup} (call $tcr) (i32.add ${load('cleanup')} (i32.const 1)))
          (call $inspect (i32.const 6))
          (call $park) (return (i32.const -1) (local.get $count))))
      (call $site (if (result i32) (i32.eq (local.get $version) (i32.const 1)) (then (i32.const 4102)) (else (i32.const 4112))))
      ;; @site 4102,4112 run resumed-inspection
      (call $inspect (i32.const 5))
      ${omitRestore?'':'(call $pop)'}
      (call $inspect (i32.const 7))
      (local.set $value0 (if (result i32) (local.get $count)
        (then (i32.load ${load('mv_base')})) (else (i32.const 65))))
      (call $park) (local.get $value0) (local.get $count))
    (func $deep_run (param $depth i32)
      (drop (call $enter (i32.const 41) (i32.const 1) (i32.const 4141)
        (i32.const 44) (call $root) (i32.const 444)))
      (if (i32.gt_u (local.get $depth) (i32.const 1))
        (then
          ;; @site 4141 deep_run recursive-call
          (call $deep_run (i32.sub (local.get $depth) (i32.const 1))))
        (else
          (call $site (i32.const 4142))
          (call $inspect (i32.const 8))
          ;; @site 4142 deep_run host-suspension
          (drop (call $suspend (i32.const 1) (i32.const 0) (call $root)))
          (call $site (i32.const 4143))
          ;; @site 4143 deep_run resumed-inspection
          (call $inspect (i32.const 9))))
      (call $pop))
    (func (export "deep") (result i32)
      (call $admit) (call $deep_run (i32.const 8)) (call $park) (i32.const 0))
    (func (export "outer") (param i32 i32 i32) (result i32 i32)
      (return_call $run (local.get 0) (local.get 1) (local.get 2) (i32.const 1)))
    (func (export "new_outer") (param i32 i32 i32) (result i32 i32)
      (return_call $run (local.get 0) (local.get 1) (local.get 2) (i32.const 2))))`;
}
