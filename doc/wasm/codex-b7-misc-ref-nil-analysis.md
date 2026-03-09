# Codex Analysis Request: B7 — XBADKEYS + `%ERR-DISP` Crash at Startup

**Scope: READ-ONLY ANALYSIS. You MAY suggest a plan and code fixes in your report. Change no files.**

---

## Context

The CCL WASM32 port has now fixed bugs B1–B6. Startup reaches `TOPLEVEL-LOOP`, establishes a catch frame, and funcalls `TOPLEVEL-LOOP` (entry 6573). The previous crash (`_SPkeyword_bind` unreachable trap, B5) is resolved — `_SPkeyword_bind` no longer traps, but now **properly signals XBADKEYS** (error 153, `errors.s:214`) because the keyvect slot is NIL in rebind-created function stubs. Then `%ERR-DISP` crashes trying to handle the error.

Two distinct failures:

1. `_SPkeyword_bind` signals XBADKEYS because the function object for a keyword-accepting function has `keyvect = NIL` (slot 2 of a 3-slot stub created by the rebind path)
2. `_SPksignalerr` dispatches through `%ERR-DISP`, which crashes on `misc_ref(NIL, 256)` — a condition system dispatch table is NIL

---

## Error Output (verbatim)

```
TL: MKCATCH1V

TL: FUNCALL nfn=0x878bfd66 e=000019ad

=== STATE DUMP: ksignalerr ===
  imm0     = 0x00000000
  imm1     = 0x00000000
  nargs    = 0x00000008
  rctx     = 0x00000000
  arg_z    = 0x878dffb5
  arg_y    = 0x00000264
  arg_x    = 0x00000000
  temp0    = 0x00000000
  temp1    = 0x00000000
  nfn      = 0x878c2d36
  vsp      = 0x0021dffc
  Rfn      = 0x878c2d36
  allocptr = 0x00000000
  Rsp      = 0x00000000
  Rlr      = 0x00000000
  Rpc      = 0x00000000
  spill: sp=0x0023ec90 base=0x0021eec0 limit=0x0023eec0 depth=140
  catch_top=0xffe1ff66 db_link=0x00000000 pending_throw=0x00000000
  VSP=0x0021dffc top: 0x04000001 0x04000001 0x878dffe6 0x00000010
  spill_push=1012 spill_pop=872
  last_cpr: e=6573 s=4 val=0x0417c096
=== END STATE DUMP ===
  fname=0x00000000
  errcode=0x00000000 datum=0x00000264 ft=4
  expected=0x878dffb5 ft=5 (0x0417c096 0x00000000)

misc_ref: bad tag obj=0x04000001 ft=0x00000001 idx=00000100

wasm_ccl_start_lisp trapped: RuntimeError: unreachable
RuntimeError: unreachable
    at subprims.wasm._SPmisc_ref (wasm://wasm/subprims.wasm-00165226:wasm-function[58]:0x723c)
    at wasmcl.wasm.wasm_call_subprim_fixnum (wasm://wasm/wasmcl.wasm-002a396e:wasm-function[160]:0xbedf)
    at wasm://wasm/00b980ee:wasm-function[218]:0xbdf83
    at subprims.wasm.wasm_call_function_value (wasm://wasm/subprims.wasm-00165226:wasm-function[27]:0x3fad)
```

---

## Decoded Values

| Register/Field | Raw Value | Decoded |
|---|---|---|
| `nargs` | `0x00000008` | fixnum 2 (two error arguments) |
| `arg_y` (error number) | `0x00000264` | **fixnum 153 = XBADKEYS** (`errors.s:214`) |
| `arg_z` (error arg) | `0x878dffb5` | cons cell, fulltag 5 — keyword info |
| `arg_x` | `0x00000000` | fixnum 0 (unused for nargs=2) |
| `nfn` / `Rfn` | `0x878c2d36` | misc object (fulltag 6) — the keyword-accepting function |
| `fname` (temp1) | `0x00000000` | fixnum 0 (not set) |
| `last_cpr` | `e=6573` | TOPLEVEL-LOOP |
| `catch_top` | `0xffe1ff66` | valid (non-zero, non-nil) |
| `pending_throw` | `0x00000000` | none |
| `arg_z` cons | `(0x0417c096 . 0x00000000)` | car=misc obj, cdr=fixnum 0 |
| misc_ref crash | `obj=0x04000001 idx=256` | NIL_VALUE, index 256 |
| VSP top 4 | `NIL NIL 0x878dffe6 0x10` | two nils, a misc obj, fixnum 4 |

**Key decode**: With `nargs=2`, the CCL error convention puts the error number in `arg_y`. `0x264 >> 2 = 153 = XBADKEYS`. This is `_SPkeyword_bind` signaling a bad-keywords error because the function's keyvect (slot 2) is NIL.

---

## Two Distinct Failures

### Failure 1: XBADKEYS from `_SPkeyword_bind`

The error number is **XBADKEYS = 153** (`errors.s:214`). This is signaled by `_SPkeyword_bind` when keyword argument validation fails.

**Root cause**: The B5 fix stopped `_SPkeyword_bind` from hitting `unreachable` traps, but the underlying problem persists — **keyvect is NIL** in rebind-created function stubs. The rebind paths (`wasm_force_rebind_scan` at `wasm-kernel-stubs.c:6775` and `wasm_set_symbol_function_entry` at `wasm-kernel-stubs.c:888`) create new 3-slot function objects with `slot[2] = nil` when no existing `subtag_function` is present. This means:

1. `_SPkeyword_bind` reads `keyvec = deref(Rfn, 3)` → gets NIL (`wasm-subprims-provider.c:7263`)
2. `keyvec == nil_value` → `keyvec_len = 0` → no keyword descriptors
3. Any keyword arguments passed are unrecognized → XBADKEYS signaled (`wasm-subprims-provider.c:7344`)

The function being called (`Rfn = 0x878c2d36`) accepts keywords but its function object was replaced by a 3-slot stub during rebind, losing the keyvect.

**Which function?** `TOPLEVEL-LOOP` calls:

```lisp
#+wasm32-target
(defun toplevel-loop ()
  (loop
    (runtime-bridge-pump-commands)          ;; ← called first, no args
    (let ((yielded
           (catch :wasm-yield
             (progn
               (if (eq (catch :toplevel
                         (read-loop :break-level 0))    ;; ← keyword call
                       $xstkover)
                 (format t "~&;[Stacks reset due to overflow.]")
                 (toplevel))
               nil))))
      (when yielded
        (return yielded)))))
```

`runtime-bridge-pump-commands` is called first with no arguments. On WASM, this is the version at `l1-readloop-lds.lisp:1320`:
```lisp
(defun runtime-bridge-pump-commands (&key (max-commands 4))
  (loop repeat max-commands do
    (multiple-value-bind (bytes status) (runtime-command--poll-frame)
      (declare (ignore status))
      (when (null bytes)
        (return))
      (let* ((frame (runtime-command--decode-frame bytes)))
        (when frame
          (runtime-command--dispatch frame)))))
  nil)
```

`runtime-bridge-pump-commands` itself accepts `&key` but is called with NO keyword args from `toplevel-loop`. However, `_SPkeyword_bind` still runs for keyword-accepting functions even with zero keyword args — it validates the keyword protocol. With `keyvect = NIL`, the function appears to accept no keywords, but the compiler generated code expecting keyword processing. The zero-arg call could still trigger XBADKEYS depending on how `_SPkeyword_bind` handles the `keyvec_len = 0` path.

Alternatively, if `runtime-bridge-pump-commands` returns successfully (since no actual keywords are passed), the next keyword call is `(read-loop :break-level 0)` — which passes `:break-level`. If `read-loop`'s function object is a 3-slot stub with `keyvect = NIL`, passing `:break-level` would definitely trigger XBADKEYS.

Note: `load-image.mjs` and `deterministic-launch.mjs` do NOT auto-retry `start_lisp`; each script calls it once (`load-image.mjs:286`, `deterministic-launch.mjs:479`). Two crashes in the output means two separate invocations.

### Failure 2: The `misc_ref` on NIL crash

After `_SPksignalerr` fires, it dispatches through `%ERR-DISP`:

```c
// wasm-subprims-provider.c:5894
LispObj errdisp = wasm_nrs_symbol_lispobj(&nrs_ERRDISP);
// ... validates errdisp symbol and fcell ...
reentering_errdisp = 1;
wasm_call_lisp_function(tcr, errdisp);   // calls %ERR-DISP
reentering_errdisp = 0;
```

`%ERR-DISP` runs compiled Lisp code. That code (wasm-function[218] in module `0x00b980ee`) tries to do `misc_ref(obj, 256)` where `obj = 0x04000001 = NIL`. The `_SPmisc_ref` subprim rejects this because NIL has `fulltag_nil = 1`, not `fulltag_misc = 6`.

`misc_ref(NIL, 256)` — index 256 is suspicious. This likely means:
- A global variable that should hold a vector is NIL (uninitialized)
- The code is doing something like `(svref *some-table* index)` where `*some-table*` is NIL
- Possible candidates: condition class vector, error handler table, type-predicate dispatch table

---

## Invariant Gate Status

The build's invariant gate iterated all 4756 runtime module functions and called `wasm_set_symbol_function_entry` for each:

```
[invariant] fcell gate: 2600 set, 2156 not found (4756 runtime entries)
```

Of the 2156 not found:
- ~344 are `(:INTERNAL ...)` forms (closures/local functions — not top-level symbols)
- ~1212 are `(METHOD ...)` forms (CLOS method specializations — stored in generic functions)
- ~6 are `#'...` forms
- **~594 are genuine symbol names** that `wasm_set_symbol_function_entry` couldn't locate via package-based lookup OR heap scan

The 4-level lookup in `wasm_set_symbol_function_entry` (line 837 of `wasm-kernel-stubs.c`):
1. Search CCL package hash table
2. Search COMMON-LISP package hash table
3. Search all package hash tables
4. O(N) heap scan for symbol with matching pname

All 4 levels fail for those ~594 functions. This means their symbols either:
- Were never interned during FASL loading (xfunction rejection cascade)
- Are in internal package slots that the hash-table walk doesn't reach
- Have pnames with different byte encoding than the manifest strings

---

## Key Files to Read

1. **`lisp-kernel/wasm-subprims-provider.c`**
   - `_SPksignalerr` (line 5710) — error dispatch, ERRDISP invocation
   - `_SPmisc_ref` (line 3682) — the crash point
   - `_SPwasm_udf_stub` (line 5963) — called when a UDF function is invoked

2. **`lisp-kernel/wasm-kernel-stubs.c`**
   - `wasm_set_symbol_function_entry` (line 837) — the 4-level symbol lookup
   - `wasm_find_symbol_in_all_packages_bytes` — package table walk
   - `wasm_find_symbol_named_bytes_scan` — heap scan fallback
   - `wasm_force_rebind_scan` (~line 6762) — force-rebind during image build

3. **`level-1/l1-readloop-lds.lisp`**
   - `toplevel-loop` (line 29) — WASM toplevel
   - `runtime-bridge-pump-commands` (line 1320) — first function called
   - `runtime-command--poll-frame` (line ~1290) — helper that uses `external-call`

4. **`level-1/l1-error-system.lisp`** (or equivalent) — `%ERR-DISP` definition, condition class dispatch. The `misc_ref(NIL, 256)` crash is INSIDE `%ERR-DISP`, suggesting the condition system's dispatch tables are NIL.

5. **`scripts/wasm/lib/make-real-image.mjs`**
   - Invariant gate (line 1886) — iterates all runtime functions
   - Force-rebind invocation
   - FASL loading phase

6. **`lisp-kernel/errors.s`** — error number definitions. Line 214: `XBADKEYS = 153`. Also `_SPkeyword_bind` in `wasm-subprims-provider.c` at lines 7255 and 7344 where XBADKEYS is signaled.

---

## Questions to Answer

1. **Which function triggers XBADKEYS?** `Rfn = 0x878c2d36` is the function whose keyvect is NIL. Is this `runtime-bridge-pump-commands` (called with 0 args but still runs `_SPkeyword_bind`), `read-loop` (called with `:break-level 0`), or something deeper? Can you determine from the stack trace?

2. **Why does `_SPkeyword_bind` signal XBADKEYS with zero keyword args?** When `runtime-bridge-pump-commands` is called with NO keyword arguments from `toplevel-loop`, does `_SPkeyword_bind` still signal XBADKEYS when `keyvect = NIL`? Or does the `keyvec_len = 0` path succeed silently for zero keywords? If the zero-keyword path succeeds, the fault is on the `(read-loop :break-level 0)` call instead.

3. **Why does `%ERR-DISP` crash with `misc_ref(NIL, 256)`?** What data structure in the condition system would have index 256 and could be NIL? Possible candidates:
   - `*condition-class-table*` or similar condition type registry
   - A type-predicate dispatch vector
   - `%ERR-DISP`'s internal lookup table mapping error numbers to condition classes
   - If `%ERR-DISP` itself is a stub or corrupted function, it might access nonsensical fields

4. **Is the condition system initialized?** After `RESTORE-LISP-POINTERS` runs, are the condition system's global tables properly restored? The `l1-error-system.lafsl` FASL should have been loaded during image build — was it? Are its global variables (vectors, hash tables) correctly saved in the image?

5. **How should the rebind path preserve keyvects?** The current 3-slot stub allocations set `slot[2] = nil`. The keyvect data exists in the compiled module metadata (the WASM module's function table contains keyword vector information). Can the invariant gate or force-rebind extract keyvect from the module metadata and install it in the function object? Or should the fix be different — e.g., having the image-fixup phase preserve keyvect from existing function objects?

6. **Are there two independent problems?** Even if we fix the XBADKEYS (by preserving keyvects), we still need `%ERR-DISP` to work for other errors. Is `misc_ref(NIL, 256)` caused by a condition system table being NIL (a separate initialization bug), or is it caused by the same rebind-stub issue affecting `%ERR-DISP`'s own closed-over data?

7. **Suggest fixes.** Based on your analysis, provide code changes for:
   - Preserving or reconstructing keyvects in rebind-created function stubs
   - Fixing the `%ERR-DISP` `misc_ref(NIL, 256)` crash
   - Any other changes needed to get startup past this point

---

## Additional Context

### Build pipeline summary

1. Kernel + subprims compiled (clean)
2. Boot modules: ~2189 entries installed
3. Runtime modules: ~4756 entries
4. Cold-boot-init: passes
5. 41 FASLs loaded successfully
6. Image fixup: 32 `misc_alloc: reserve failed` (pre-GC, same as before)
7. Force-rebind: 2664 of 4756 runtime entries matched
8. Pre-toplfunc GC: freed 1.78 GB
9. **Invariant gate: 2600 set, 2156 not found**
10. Pre-save GC
11. root.image saved (2.1 GiB)

### Launch pipeline

1. Load root.image into WASM memory
2. Compile 36 merged module binaries
3. Fill 8675 function table entries
4. `start_lisp()` → `RESTORE-LISP-POINTERS` → `wasm_toplevel_loop()`
5. `TOPLEVEL-LOOP` catch frame → funcall → **ksignalerr → misc_ref on NIL → TRAP**

### Bug tracker

| Bug | Description | Status |
|-----|-------------|--------|
| B1 | Boot modules not installed (default=-1) | FIXED |
| B2 | malloc vs Lisp heap for misc_alloc | FIXED |
| B3 | No pre-save GC | FIXED |
| B4 | pending_throw propagation | FIXED |
| B5 | `_SPkeyword_bind` unreachable trap (keyvect destroyed by rebind) | FIXED (no longer traps) |
| B6 | XFUNBND for RUNTIME-COMMAND--* functions | FIXED (invariant gate expanded) |
| B7a | XBADKEYS (153): keyvect=NIL in rebind-created 3-slot stubs | **THIS BUG** |
| B7b | `misc_ref(NIL, 256)` inside `%ERR-DISP` when handling B7a | **THIS BUG** |

### Entry index reference

- 6573 = `TOPLEVEL-LOOP`
- 6679 = `RUNTIME-BRIDGE-PUMP-COMMANDS`
- 6678 = `RUNTIME-COMMAND--POLL-FRAME`
- 6633 = `RUNTIME-COMMAND--DECODE-FRAME`
- 6677 = `RUNTIME-COMMAND--DISPATCH`
- 8314 = `%ERR-DISP`
- 8967 = `RESTORE-LISP-POINTERS`

---

## Keyvect Preservation Problem — Detail

The B5 fix made `_SPkeyword_bind` diagnostic instead of trapping, and the B5 in-place patching preserves keyvects when `fcell` already has a `subtag_function` object. But the problem is the **else branch** — when the fcell does NOT have a subtag_function (e.g., it's a UDF pseudofunction or xfunction):

```c
// wasm-kernel-stubs.c:888 — wasm_set_symbol_function_entry, fcell path
} else {
  LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)3);
  if (fn == lisp_nil) return -4;
  LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
  fn_data[0] = entry;   // slot 0: entrypoint
  fn_data[1] = entry;   // slot 1: codevec
  fn_data[2] = lisp_nil; // slot 2: keyvect = NIL ← THE PROBLEM
  rawsym->fcell = fn;
}
```

And similarly in `wasm_force_rebind_scan` at line 6775:
```c
} else {
  LispObj fn = wasm_misc_alloc(tcr, subtag_function, (signed_natural)3);
  if (fn != lisp_nil) {
    LispObj *fn_data = (LispObj *)((BytePtr)fn + misc_data_offset);
    fn_data[0] = entry_val;
    fn_data[1] = entry_val;
    fn_data[2] = lisp_nil;   // keyvect = NIL ← SAME PROBLEM
    rawsym->fcell = fn;
  }
}
```

These paths are hit when FASL loading failed to create a proper function object (xfunction rejection by `%defun`) and the symbol's fcell is still a UDF pseudofunction. The new stub gets the right entry index but loses the keyvect.

The keyvect data IS available in the compiled module manifests — each function entry in the WASM module has keyword parameter information. But the C-side rebind paths have no access to this metadata; they only know the entry index.

---

**Deliverable: Analysis identifying (a) which function triggers XBADKEYS and why, (b) why `%ERR-DISP` crashes on `misc_ref(NIL, 256)`, (c) how to preserve/reconstruct keyvects in rebind stubs, and (d) suggested code changes to resolve both failures so startup reaches the REPL.**
