# Codex Analysis Request: _SPkeyword_bind Trap at Startup

**Scope: READ-ONLY ANALYSIS. You may suggest code changes in your final report. Change no files.**

---

## Context

The CCL WASM32 port now successfully:
1. Builds `root.image` (cold-boot-init passes, 41 FASLs loaded, image serialized)
2. Launches via `load-image.mjs` (image loaded, 8675 module table entries filled)
3. Enters `start_lisp()` → `RESTORE-LISP-POINTERS` (no throw) → `wasm_toplevel_loop()`
4. Toplevel loop establishes catch frame (`MKCATCH1V`)
5. Funcalls toplevel function `TOPLEVEL-LOOP` (entry 6573)

Then it **traps** inside `_SPkeyword_bind`.

---

## Error Output

```
TL: MKCATCH1V

TL: FUNCALL nfn=0x878bf476 e=000019ad

wasm_ccl_start_lisp trapped: RuntimeError: unreachable
RuntimeError: unreachable
    at subprims.wasm._SPkeyword_bind (wasm://wasm/subprims.wasm-00164566:wasm-function[152]:0x10f68)
    at wasmcl.wasm.wasm_call_subprim_fixnum (wasm://wasm/wasmcl.wasm-002a36de:wasm-function[160]:0xbedf)
    at wasm://wasm/00294c8a:wasm-function[1300]:0x7ad6c
    at subprims.wasm.wasm_call_function_value (wasm://wasm/subprims.wasm-00164566:wasm-function[27]:0x3fad)
    at subprims.wasm.wasm_call_function_or_symbol (wasm://wasm/subprims.wasm-00164566:wasm-function[21]:0x2998)
    at subprims.wasm._SPfuncall (wasm://wasm/subprims.wasm-00164566:wasm-function[30]:0x52e8)
    at wasmcl.wasm.wasm_call_subprim_fixnum (wasm://wasm/wasmcl.wasm-002a36de:wasm-function[160]:0xbedf)
    at wasmcl.wasm.wasm_funcall_common (wasm://wasm/wasmcl.wasm-002a36de:wasm-function[351]:0x10143)
    at wasmcl.wasm.wasm_funcall0 (wasm://wasm/wasmcl.wasm-002a36de:wasm-function[415]:0x14ebb)
    at wasm://wasm/00129452:wasm-function[1117]:0x2f4d8
```

Entry 0x19ad = 6573 = `TOPLEVEL-LOOP`.

---

## Call Chain Reconstruction

Bottom-up from the stack:

1. **wasm-function[1117] at module 0x00129452** — this is `TOPLEVEL-LOOP` (entry 6573) compiled code. It calls `wasm_funcall0` (zero-arg funcall helper).

2. **wasm_funcall0 → wasm_funcall_common → _SPfuncall** — standard funcall dispatch. Resolves the callee, reads entry index from function object slot 1, dispatches.

3. **wasm_call_function_or_symbol → wasm_call_function_value** — validates function object, extracts entry index, calls `wasm_call_entry_index()`.

4. **wasm-function[1300] at module 0x00294c8a** — callee compiled code executes. This function accepts keyword arguments, so it calls `_SPkeyword_bind`.

5. **wasm_call_subprim_fixnum → _SPkeyword_bind** — **TRAP HERE**.

### Identifying the callee

From the WASM `TOPLEVEL-LOOP` Lisp definition:

```lisp
#+wasm32-target
(defun toplevel-loop ()
  (loop
    (runtime-bridge-pump-commands)
    (let ((yielded
           (catch :wasm-yield
             (progn
               (if (eq (catch :toplevel
                         (read-loop :break-level 0))  ;; ← keyword arg call
                       $xstkover)
                 (format t "~&;[Stacks reset due to overflow.]")
                 (toplevel))
               nil))))
      (when yielded
        (return yielded)))))
```

The call `(read-loop :break-level 0)` passes keyword `:break-level`. The compiler generates `_SPkeyword_bind` to process the keyword pair. This makes `read-loop` the most likely callee that triggers the trap.

However, `runtime-bridge-pump-commands` is called first. If that function (or anything it calls) also accepts keywords, it could be the one trapping. The `read-loop` hypothesis requires confirming that `runtime-bridge-pump-commands` returns successfully.

---

## _SPkeyword_bind Implementation

File: `lisp-kernel/wasm-subprims-provider.c`, line 7225.

```c
void _SPkeyword_bind(void)
{
  TCR *tcr = wasm_get_current_tcr();
  if (tcr == NULL) { wasm_subprims_trap(); }             // trap point 1

  LispObj raw_nargs = wasm_reg(tcr, nargs);
  LispObj raw_prev = wasm_reg(tcr, imm0);
  LispObj keyword_flags = wasm_reg(tcr, arg_y);
  if (tag_of(raw_nargs) != tag_fixnum ||
      tag_of(raw_prev) != tag_fixnum ||
      tag_of(keyword_flags) != tag_fixnum) {
    wasm_subprims_trap();                                 // trap point 2
  }

  signed_natural nargs_count = unbox_fixnum(raw_nargs);
  signed_natural prev_count = unbox_fixnum(raw_prev);
  if (nargs_count < 0 || prev_count < 0) {
    wasm_subprims_trap();                                 // trap point 3
  }

  // ... key_value_count computed ...

  LispObj fn_obj = wasm_reg(tcr, Rfn);
  if (fulltag_of(fn_obj) != fulltag_misc) {
    wasm_subprims_trap();                                 // trap point 4
  }

  LispObj keyvec = deref(fn_obj, 3);                     // ← reads slot 2
  signed_natural keyvec_len = 0;
  if (keyvec != (LispObj)nil_value) {
    if (fulltag_of(keyvec) != fulltag_misc) {
      wasm_subprims_trap();                               // trap point 5
    }
    keyvec_len = header_element_count(header_of(keyvec));
    if (keyvec_len < 0 || keyvec_len > 256) {
      wasm_subprims_trap();                               // trap point 6
    }
  }

  LispObj *stack_ptr = (LispObj *)wasm_reg(tcr, vsp);
  if (stack_ptr == NULL) {
    wasm_subprims_trap();                                 // trap point 7
  }

  // ... rest of keyword processing ...
}
```

`wasm_subprims_trap()` is `__builtin_trap(); __builtin_unreachable();` — compiles to WASM `unreachable` instruction.

---

## Function Object Layout

For a WASM CCL misc object tagged with `fulltag_misc = 6`:

| Offset from header | `deref` index | Content |
|---|---|---|
| +0 | 0 (header_of) | header word |
| +4 | 1 | slot 0: entrypoint (fixnum) |
| +8 | 2 | slot 1: code-vector (fixnum) |
| +12 | 3 | slot 2: keyvect (simple-vector or NIL) |
| +16 | 4 | slot 3: closed vars... |

ARM64 confirmation — `arm64-spentry.s` line 2690:
```asm
__(ldr temp2,[fn,#misc_data_offset+(2*node_size)])
```
= `fn + (-2) + 2*4` = `fn + 6` = `(addr+6) + 6` = `addr + 12` → slot 2, same as `deref(fn, 3)`.

So the keyvect offset is consistent between ARM and WASM.

---

## Trap Point Analysis

The trap at WASM offset `0x10f68` in `_SPkeyword_bind` must be one of the 7 `wasm_subprims_trap()` calls. The most likely candidates:

### Hypothesis A: Trap point 5 — keyvec is non-nil but not fulltag_misc

If the function object for `read-loop` has only 2 data slots (entry, codevec), then `deref(fn_obj, 3)` reads past the object boundary. The value read would be whatever follows in memory — a GC forwarding pointer, another object's header, or uninitialized memory. If that value is non-nil and not tagged as `fulltag_misc`, trap point 5 fires.

**Why would the function object have only 2 slots?** If `read-loop`'s function object was created by:
- `wasm_set_symbol_function_entry()` — always allocates 2-slot functions
- `wasm_misc_alloc(tcr, subtag_function, 2)` — always 2 slots
- Image-fixup fallback with wrong `fnSlots`
- Any path that doesn't preserve the original FASL-created function object

The FASL loader should create function objects with the correct slot count, but if image fixup or force-rebind overwrote the fcell with a 2-slot stub, the keyvect would be lost.

### Hypothesis B: Trap point 2 — register corruption

If `nargs`, `imm0`, or `arg_y` don't contain fixnums when `_SPkeyword_bind` is called, trap point 2 fires. This would indicate the compiled code that calls `_SPkeyword_bind` isn't setting up the registers correctly — a compiler or calling convention bug.

### Hypothesis C: Trap point 7 — VSP null

If the value stack pointer is NULL, trap point 7 fires. This could happen if `RESTORE-LISP-POINTERS` or an earlier function corrupted VSP.

---

## Key Files to Read

- `lisp-kernel/wasm-subprims-provider.c` — `_SPkeyword_bind` (line 7225), `wasm_subprims_trap` (line 71), `wasm_call_function_value` (line 2409)
- `lisp-kernel/wasm-kernel-stubs.c` — `start_lisp` (line 3301), `wasm_toplevel_loop` (line 652), `wasm_set_symbol_function_entry` (line 837)
- `level-1/l1-readloop-lds.lisp` — `toplevel-loop` (line 29), `read-loop` definition
- `compiler/WASM/wasm2.lisp` — keyword argument compilation, function object slot allocation
- `lisp-kernel/arm64-spentry.s` — `_SPkeyword_bind` ARM reference implementation (line 2666) for calling convention comparison
- `scripts/wasm/lib/make-real-image.mjs` — image-fixup scan (line 1260), force-rebind (line 1440+), invariant gate (line 1885+)

---

## Questions to Answer

1. **Which trap point fires?** Can you determine from the WASM offset `0x10f68` which of the 7 `wasm_subprims_trap()` calls is hit? Or add diagnostic logging before each trap to identify it.

2. **Is the function object for the callee (likely `read-loop`) correctly formed?** Does it have enough slots to hold a keyvect at slot 2? Was it created by FASL loading (correct) or overwritten by image-fixup/force-rebind (potentially wrong slot count)?

3. **Does the image-fixup or force-rebind phase overwrite FASL-created function objects?** The image-fixup scan (make-real-image.mjs:1260) updates entry indices in-place for existing function objects, or allocates new ones via `wasm_misc_alloc`. If `read-loop` already had a correct function object from FASL loading, the fixup should only update slots 0-1 (entry indices), preserving the keyvect. But if the fixup path allocated a NEW function object (the `miscAllocFn` branch), the new object would have slots 0-1 set but slot 2+ initialized to NIL (no keyvect).

4. **Is the ARM calling convention for `_SPkeyword_bind` faithfully reproduced?** Compare register setup between ARM's `_SPkeyword_bind` entry (arm64-spentry.s:2666) and the WASM version. On ARM, `nargs` = total arg count, `imm0` = count of positional args (required + optional), `arg_y` = keyword flags. Does the WASM compiler set these registers correctly before calling the subprim?

5. **Could `RESTORE-LISP-POINTERS` have silently corrupted state?** It ran without throwing, but did it actually complete its work? After image load, package hash tables need rehashing — if that failed silently, symbol lookups (including keyword symbol comparisons in `_SPkeyword_bind`) would fail.

6. **Suggest a fix.** Based on your analysis, what code change(s) would resolve the trap? Consider:
   - Adding diagnostic logging before each `wasm_subprims_trap()` in `_SPkeyword_bind` to identify the exact trap point
   - Ensuring function objects preserve keyvect slots through image-fixup
   - Fixing any register setup mismatch between the compiler output and subprim expectations

---

## Additional Context

### Build pipeline (abbreviated)

1. Install boot modules (1117 entries, strict) ← fixed this session
2. Install runtime modules (7560 entries)
3. cold-boot-init ← now passes
4. Load 41 FASLs
5. Image fixup (entry index rebind)
6. Force-rebind
7. Pre-toplfunc GC (frees 1.78 GB)
8. Invariant gate (RUNTIME-BRIDGE-PUMP-COMMANDS, %ERR-DISP via wasm_set_symbol_function_entry)
9. Set toplevel function (entry 6573 = TOPLEVEL-LOOP)
10. Pre-save GC
11. Save root.image (2.1 GiB)

### Launch pipeline

1. Read startup-plan.json
2. Load root.image into WASM memory
3. Compile 36 merged module binaries
4. Fill 8675 function table entries
5. `wasm_ccl_start_lisp()` → `start_lisp()` → `RESTORE-LISP-POINTERS` → `wasm_toplevel_loop()` → **TRAP**

### wasm_misc_alloc reserve failures during build

During the image-fixup phase, 34 `WASM misc_alloc: reserve failed` messages appeared. The heap was nearly full at that point (before the pre-toplfunc GC freed 1.78 GB). This means 34 function objects that needed allocation couldn't be created. These are symbols in the boot module `rebindMap` whose fcells were NOT `subtag_function` — they remained as UDF pseudofunctions. If `read-loop` was among these 34 failed allocations, its fcell would point to a UDF pseudofunction (not a real function object with keyvect).

However, FASL loading happens AFTER image fixup. If `read-loop` is defined in a FASL, the FASL loader would overwrite the failed fixup with a correct function object. Only functions NOT redefined by FASLs would be affected.

### Entry index reference

- 6573 = `TOPLEVEL-LOOP`
- 5892 = `TOPLEVEL`
- 8967 = `RESTORE-LISP-POINTERS`
- 6679 = `RUNTIME-BRIDGE-PUMP-COMMANDS`
- 8314 = `%ERR-DISP`

---

**Deliverable: Analysis identifying the exact trap point, root cause, and suggested code changes to resolve the `_SPkeyword_bind` trap so startup reaches the REPL.**
