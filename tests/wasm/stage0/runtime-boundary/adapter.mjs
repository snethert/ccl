// Emitted-language prototype of C-boundary restoration using final try_table EH.
// The D3 call-argument candidates are not selected by this fixture.
export function adapterWat({ omitStackRestore = false, omitRootRestore = false } = {}) {
  const save = [24, 28, 32, 36, 40].map((off, i) => `(local.set $s${i} (i32.load offset=${off} (local.get $tcr)))`).join('\n');
  const restore = [24, 28, 32, 36, 40].map((off, i) => omitRootRestore && off === 24 ? '' : `(i32.store offset=${off} (local.get $tcr) (local.get $s${i}))`).join('\n')
    + (omitStackRestore ? '' : '\n(global.set $sp (local.get $savedSp))');
  return `(module
    (import "env" "memory" (memory 2 16 shared))
    (import "kernel" "__stack_pointer" (global $sp (mut i32)))
    (import "kernel" "get_tcr" (func $get_tcr (result i32)))
    (import "kernel" "exit_helper" (func $helper (param i32 i32) (result i32)))
    (import "emitted" "exit" (tag $exit (param i32)))
    (import "emitted" "cleanup" (tag $cleanup (param i32)))
    (func $invoke (export "invoke") (param $mode i32) (param $restart i32) (result i32 i32)
      (local $tcr i32) (local $savedSp i32) (local $caught i32)
      (local $s0 i32) (local $s1 i32) (local $s2 i32) (local $s3 i32) (local $s4 i32)
      (local.set $tcr (call $get_tcr))
      (local.set $savedSp (global.get $sp))
      ${save}
      (local.set $caught
        (block $handler (result i32)
          (try_table (catch $exit $handler)
            (drop (call $helper (local.get $mode) (i32.const 12345))))
          (i32.const 0)))
      ${restore}
      (if (local.get $caught)
        (then
          (i32.store offset=80 (local.get $tcr)
            (i32.add (i32.load offset=80 (local.get $tcr)) (i32.const 1)))
          (if (i32.eq (local.get $restart) (i32.const 1))
            (then (throw $exit (local.get $caught))))
          (if (i32.eq (local.get $restart) (i32.const 2))
            (then (throw $cleanup (local.get $caught))))))
      (if (result i32) (i32.eqz (i32.load offset=44 (local.get $tcr)))
        (then (i32.const 65))
        (else (i32.load (i32.load offset=48 (local.get $tcr)))))
      (i32.load offset=44 (local.get $tcr)))
    (func (export "outer") (param $mode i32) (param $restart i32) (result i32 i32)
      (local $tcr i32)
      (local.set $tcr (call $get_tcr))
      (block $cleanupHandler (result i32)
        (block $exitHandler (result i32)
          (try_table (catch $exit $exitHandler) (catch $cleanup $cleanupHandler)
            (return (call $invoke (local.get $mode) (local.get $restart))))
          (unreachable))
        (drop)
        (i32.store offset=84 (local.get $tcr) (i32.const 1))
        (return (i32.const -101) (i32.const 0)))
      (drop)
      (i32.store offset=84 (local.get $tcr) (i32.const 2))
      (i32.const -102) (i32.const 0)))`;
}
