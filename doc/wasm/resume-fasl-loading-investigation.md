# Resume Prompt: FASL Loading Investigation (v16)

**Project:** CCL WASM32 port
**Working directory:** `/Users/buildsomething/Source/ccl`
**Branch:** `wasm-port` (HEAD: `47811027`)
**Role:** You are the kernel engineer debugging the WASM32 port of Clozure Common Lisp.

---

## Read these first

1. `CLAUDE.md` — standing rules, build commands, architecture notes
2. `TODO.md` — full bug-fix history, current status, resolved blockers
3. `doc/wasm/debugging.md` — debugging guide

---

## Current state

**Cold-boot-init is RESOLVED.** The v15.3 fix (commit `47811027`) made `wasm_run_cold_boot_init` return 0. The build pipeline now proceeds through:

1. Boot image loaded
2. 1104 boot modules installed (5 known failures: entries 679, 683, 688, 696, 975 — import type mismatches)
3. 7557/7557 runtime modules installed (0 failed)
4. 170 null table slots filled with trap stub
5. cold-boot-init: startup-step=4131, 3 absorbed errors, returns 0
6. **FASL loading begins → FAILS on first file**

**New blocker:** `l1-cl-package.lafsl` fails with return code -72.

Working tree is clean. No uncommitted changes.

---

## The failure in detail

The last successful build log is at `/tmp/v15-build.log` (300 lines). The relevant FASL failure section (lines 201–301):

```
;Loading l1-fasls/l1-cl-package.lafsl

=== STATE DUMP: funcall-error ===
  imm1     = 0x00000164
  nargs    = 0x00000004
  arg_z    = 0x94c46bc6
  arg_y    = 0x0412c72e
  arg_x    = 0x94c46bae
  nfn      = 0x04000001        ← SUSPICIOUS: this is NOT a real function pointer
  Rfn      = 0x04000001
  spill: depth=370
  catch_top=0x00000000         ← no catch handler
  VSP top: 0x94c46bc6 0x94c46bc6 0x94c46c7e 0x00000049
  spill_push=63645 spill_pop=63275
  last_cpr: e=1087 s=0 val=0x0412c72e
=== END STATE DUMP ===

=== STATE DUMP: ksignalerr ===
  (same state — ksignalerr absorbed #4)
=== END STATE DUMP ===

FAIL: wasm_fasload_path(l1-fasls/l1-cl-package.lafsl) returned -72
```

### What -72 means

In `wasm-kernel-stubs.c:4509-4511`:
```c
(void)wasm_foreign_funcall1(tcr, fasload_fn, path);
if (tcr->wasm_pending_throw) {
    return -72;  /* fasload threw */
}
```

The C wrapper `wasm_fasload_path` successfully:
- Found the CCL package
- Found the `%FASLOAD` symbol
- Validated its fcell is a function
- Created a Lisp base-string from the path
- Called `wasm_foreign_funcall1(tcr, fasload_fn, path)` — this calls the Lisp `%FASLOAD` function

But during execution of `%FASLOAD`, `wasm_pending_throw` was set → returned -72.

### Key observations from the state dump

1. **`nfn = 0x04000001`** — This value has `fulltag_misc` (tag bits = `0x02`), but the untagged address `0x03FFFFFF` is suspiciously close to the start of the dynamic heap. It could be:
   - A GC-forwarded pointer
   - A stale reference from the boot image
   - The very first misc object allocated in the heap

2. **`last_cpr: e=1087 s=0`** — Entry 1087 was the last function called before the error. Use `node scripts/wasm/lookup-entry.mjs 1087` to identify it.

3. **`catch_top = 0x00000000`** — No catch frame is established. This is the same pattern as cold-boot-init errors: the funcall-error triggers `_SPksignalerr`, which absorbs (sets `pending_throw(16)`) because there's no catch handler. The pending_throw propagates back up to `wasm_foreign_funcall1`, which returns it to `wasm_fasload_path`.

4. **`imm1 = 0x00000164`** — This is 356 decimal. May be a FASL opcode index or buffer offset.

5. **`arg_z = 0x94c46bc6`, `arg_x = 0x94c46bae`** — These are high-memory misc-tagged pointers (above 0x90000000), which is the upper heap region. They look like legitimate Lisp objects.

6. **`arg_y = 0x0412c72e`** — Also misc-tagged. Appears in the `last_cpr` val field too.

7. **`VSP top: 0x94c46bc6 0x94c46bc6 0x94c46c7e 0x00000049`** — Note `0x00000049` (fixnum 18) on the stack, same value that appeared in cold-boot-init error #3.

### The funcall-error path

The error is `funcall-error`, not `ksignalerr` directly. Looking at `wasm-subprims-provider.c:2246-2253`:
```c
static void wasm_signal_funcall_error(TCR *tcr, signed_natural errnum, LispObj name) {
    wasm_debug_dump_state("funcall-error");
    wasm_set_reg(tcr, arg_y, box_fixnum(errnum));
    wasm_set_reg(tcr, arg_z, name);
    wasm_set_nargs_count(tcr, 2);
    _SPksignalerr();
}
```

The funcall-error is triggered in `wasm_call_function_value` when the function value fails validation (not a function, wrong tag, undefined, etc.). The most likely trigger point for `nfn=0x04000001`:
- `deref(fn_value, 1)` reads the entry index from the function — if `fn_value` is `0x04000001`, `deref(0x04000001, 1)` reads the second slot of whatever object lives at address `0x03FFFFFF`. If this isn't a real function, the entry index won't be a fixnum → `tag_of(entry) != tag_fixnum` → funcall-error with `WASM_XNOTFUN`.

---

## Investigation steps

### Step 1: Identify entry 1087

```bash
node scripts/wasm/lookup-entry.mjs 1087
```

This tells you which Lisp function is at entry 1087 — the function that was executing when the error occurred.

### Step 2: Understand 0x04000001

Decode the tagged pointer:
- `fulltag_of(0x04000001) = 0x01` → This is `fulltag_cons` (tag 1), NOT `fulltag_misc`.
- Wait — double-check: on WASM32/ARM, `tag_mask = 0x07`, so `0x04000001 & 0x07 = 0x01`.
- Tag 1 = `tag_fixnum` (odd fixnums)? No — check `wasm-arch.lisp` and `constants.h` for the exact tag mapping.
- **This needs careful tag analysis.** Read `lisp-kernel/arm/constants.h` or `level-0/WASM/wasm-arch.lisp` for the fulltag definitions.

### Step 3: Add diagnostics to `wasm_fasload_path`

Before the `wasm_foreign_funcall1` call, log:
- The `fasload_fn` value (should be a valid function pointer)
- Its entry index (`deref(fasload_fn, 1)`)
- The `path` Lisp string

After the call returns, before checking `wasm_pending_throw`, log:
- `tcr->wasm_pending_throw` value
- `tcr->wasm_gprs[nfn]` (what nfn was set to when the error occurred)

### Step 4: Check whether `%FASLOAD` needs catch frames

Look at `level-0/nfasload.lisp:959+`. The `%FASLOAD` function:
- Opens a FASL file (`%fasl-open`)
- Reads blocks (`%fasl-read-word`, `%fasl-read-long`)
- Dispatches opcodes (`%fasl-dispatch`)
- Uses `unwind-protect`

The `unwind-protect` may require catch/cleanup frames that don't exist yet. On ARM, these are established by the runtime. On WASM, `catch_top = 0` means NO catch frames exist — `unwind-protect` would fail.

**Key question:** Does `%stack-block` or `unwind-protect` (both used by `%FASLOAD`) require catch/unwind frames that the C wrapper doesn't set up?

Check how `wasm_foreign_funcall1` differs from `wasm_run_cold_boot_init` — does one set up catch frames that the other doesn't?

### Step 5: Check if the error occurs BEFORE or DURING FASL reading

The `";Loading l1-fasls/l1-cl-package.lafsl"` message comes from `%FASLOAD` itself (line 964-965 in nfasload.lisp), so the function was entered and started executing. The error happens after the loading message but before completion.

Add `%wasm-note-fasload-step` logging already exists in `%FASLOAD` (steps 100-190). Check if there's a way to read the step counter from C to see how far `%FASLOAD` got.

### Step 6: Consider the `pending_throw` state

After cold-boot-init, `pending_throw` was cleared by `wasm_run_cold_boot_init` (line 3357: `tcr->wasm_pending_throw = 0`). Then `wasm_fasload_path` calls `wasm_foreign_funcall1`, which also clears it (line 4289: `tcr->wasm_pending_throw = 0`). So the `pending_throw` detected at line 4510 must have been set DURING `%FASLOAD` execution — not a leftover.

---

## Key files

| File | What's there |
|------|-------------|
| `lisp-kernel/wasm-kernel-stubs.c:4442-4514` | `wasm_fasload_path` — the C wrapper that calls `%FASLOAD` |
| `lisp-kernel/wasm-kernel-stubs.c:4275-4308` | `wasm_foreign_funcall1` — the generic 1-arg Lisp call wrapper |
| `lisp-kernel/wasm-subprims-provider.c:2245-2253` | `wasm_signal_funcall_error` — funcall-error handler |
| `lisp-kernel/wasm-subprims-provider.c:2258-2433` | `wasm_call_function_value` — the funcall dispatcher |
| `lisp-kernel/wasm-subprims-provider.c:5363-5478` | `_SPksignalerr` — error signaling with catch_top==0 guard |
| `level-0/nfasload.lisp:959-1028` | `%FASLOAD` — the Lisp FASL loader |
| `level-0/WASM/wasm-arch.lisp` | Tag definitions, fulltag constants |
| `lisp-kernel/arm/constants.h` | C-side tag/fulltag constants |
| `scripts/wasm/lib/make-real-image.mjs:1188-1296` | JS-side FASL loading loop |
| `scripts/wasm/lookup-entry.mjs` | Entry index → function name lookup tool |

---

## Build and run commands

```bash
# Full rebuild (kernel + subprims + boot image + modules + root image)
# Takes ~40 minutes for module installation
scripts/wasm/rebuild-everything.sh

# Root image only (skip kernel/module rebuild if unchanged)
node --max-old-space-size=8192 scripts/wasm/lib/make-real-image.mjs \
  --output build/wasm32/root.image \
  --manifest-out build/wasm32/root-manifest.json \
  --modules build/wasm32/modules/wasm-module-bundle.json \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json

# Redirect output to log file (ALWAYS do this — builds produce huge output)
<build-command> 2>&1 | tee /tmp/v16-build.log

# Check log size periodically during build (CRITICAL: check every 2 min)
wc -l /tmp/v16-build.log

# Kernel-only rebuild (after editing C files)
make -C lisp-kernel/wasm32

# Subprims-only rebuild
make -C lisp-kernel/wasm32/subprims

# Check for stale artifacts
scripts/wasm/check-freshness.sh

# Lookup entry index
node scripts/wasm/lookup-entry.mjs 1087
```

---

## Working rules (from prior sessions)

1. **Monitor log size.** Check `wc -l` every 2 minutes during builds. If growth exceeds 1000 lines/min, kill and investigate. The v15 disaster produced 93M lines because state dumps were ungated.

2. **State dump cap is 10.** `wasm_debug_dump_state` in `wasm-kernel-stubs.c:1828` limits to 10 dumps globally. `_SPksignalerr` limits verbose diagnostics to first 5 calls. Both are static counters — they accumulate across cold-boot-init AND FASL loading.

3. **`pending_throw` is the unwind mechanism.** The funcall dispatcher (`wasm_call_function_value`, lines 2322/2353/2586) checks `wasm_pending_throw_p(tcr)` after every function call. When set, it short-circuits the call stack. Compiled WASM code does NOT check it — only the C funcall wrapper does.

4. **`catch_top = 0` means no error handling.** Without catch frames, any error signal → `_SPksignalerr` absorb → `pending_throw(16)` → unwind back to C caller. This was fine for cold-boot-init but is the root cause for FASL loading failure too.

5. **ARM32 is the reference architecture.** Check `compiler/ARM/` and ARM subprims for how things are supposed to work.

6. **One blocker deep.** If fixing A reveals blocker B, that's a signal to workaround A instead. Don't chase rabbit holes.

7. **The 5 known boot module failures** (entries 679, 683, 688, 696, 975) are import type mismatches and WASM validation errors. They've been present since v13 and are NOT related to the current FASL failure.

---

## Hypothesis space

**H1: Missing catch frames.** `%FASLOAD` uses `unwind-protect` (nfasload.lisp:995) and `%stack-block` (line 988). These Lisp special forms typically compile to catch/cleanup frames. If the catch frame setup subprims don't work correctly on WASM, any error inside `%FASLOAD` would find `catch_top=0` and get absorbed via `pending_throw`. This would explain why -72 is returned.

**H2: `nfn=0x04000001` is a tag/type confusion.** The funcall dispatcher tried to call something with value `0x04000001`. If this is a cons cell being treated as a function, `deref(fn_value, 1)` reads the car/cdr which won't be a fixnum → XNOTFUN error. Need to figure out WHY a non-function value ended up in `nfn`.

**H3: Entry 1087 is a function that returns a non-callable value.** The `last_cpr: e=1087 s=0` means entry 1087 was the last function called. If this function returns something unexpected (e.g., a symbol instead of a function closure), and the caller tries to funcall the return value, that would trigger funcall-error.

**H4: Stale function reference from boot image.** The boot image was built by cross-compilation. If a function cell in the boot image points to an old/wrong function object, the funcall dispatcher would see a bad `nfn` value.

---

## Immediate task

1. Run `node scripts/wasm/lookup-entry.mjs 1087` to identify the function
2. Add diagnostic logging to `wasm_fasload_path` (before/after the funcall)
3. Check the tag definitions to decode `0x04000001` precisely
4. Look at how ARM establishes catch frames before FASL loading
5. If catch frames are the issue, consider establishing a catch-all frame in `wasm_fasload_path` before calling `%FASLOAD` (similar to how the native runtime wraps toplevel calls)
