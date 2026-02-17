# Expert Prompt: Fix `%KERNEL-RESTART` Undefined During Cold-Boot-Init

## The Problem

Root image build fails with return code -6 from `wasm_run_cold_boot_init()`. The C kernel catches a `wasm_pending_throw` and reports:

```
cold-boot-init: threw
FAIL: wasm_run_cold_boot_init returned -6
```

The state dump shows `%KERNEL-RESTART` is the undefined symbol (XFUNBND error code 6). **But `%KERNEL-RESTART` being undefined is expected** — it's a level-1 function (`level-1/l1-error-signal.lisp:19`) that doesn't exist during cold-boot-init. In native CCL, cold-boot-init also runs before `%KERNEL-RESTART` exists — it just never hits any errors.

**The real bug is: what error does cold-boot-init encounter on WASM that triggers the error system?** The `%KERNEL-RESTART` XFUNBND is a secondary failure (double fault).

## State Dump Analysis

```
=== funcall-error ===
nargs=0x0000000c  (fixnum 3 — three arguments)
arg_z=0x0411df3e  arg_y=0x00004c4b  arg_x=0x00000274
nfn=0x0400016e  Rfn=0x0400016e
last_cpr: e=845 s=1 val=0x0411df3e

=== ksignalerr ===
nargs=0x00000008  (fixnum 2 — error-type + fn)
arg_z=0x0400016e  arg_y=0x00000018  (fixnum 6 = XFUNBND)
sym: %KERNEL-RESTART  fcell=0x04110006  ent=0x0000020c
```

Entry lookup results:
- **Entry 845** = `ASH` (boot module) — the function executing when the error occurred
- **Entry 524** (0x20c) = `%SHORT-FLOAT-RATIO` (boot module) — NOT `%KERNEL-RESTART`'s entry; this is likely the entry in the UDF sentinel object

**Interpretation**: Code related to `ASH` (or called from ASH's const pool) tried to funcall something that wasn't a valid function object. The funcall-error subprim tried to signal this via `ksignalerr`, which tried to call `%KERNEL-RESTART` → double fault.

## Cold-Boot-Init Steps

`%run-cold-boot-init` is defined in `level-0/nfasload.lisp:1243`. It executes these steps, with `%wasm-note-startup-step N` logging between each:

| Step | What happens | Key functions |
|------|-------------|---------------|
| 10 | Start | |
| 20 | `(%set-tcr-toplevel-function (%current-tcr) nil)` | |
| 30 | `(setq %system-locks% (%cons-population nil))` | |
| 40 | `(setq %all-packages-lock% (make-read-write-lock))` | |
| 40→50 | Execute `*xload-cold-load-functions*` — `(dolist (f ...) (funcall f))` | **Most likely crash site** |
| 50→60 | Populate early class cells via `(gethash ... %find-classes%)` | |
| 60→70 | Resize package hash tables — `(%resize-htab (pkg.itab p))` | |
| 70→80 | Apply documentation — `(apply 'set-documentation f)` | |
| 80→90 | Walk all symbols, set binding indices — `(%map-areas ...)` | |

**The crash likely occurs during step 40→50** (cold-load function execution) or step 60→70 (hash table resize), since those involve complex computation.

**NOTE**: The `%wasm-note-startup-step` macro uses `(format t ...)` which goes to Lisp `*standard-output*`. On WASM, this stream is NOT connected to the Node.js console — so **startup step output is currently invisible**. The C-level `wasm_host_log` messages DO appear (e.g., "cold-boot-init: threw"). First task: add C-level diagnostics (via `wasm_debug_dump_state` or `wasm_host_log`) to narrow the crash point, OR temporarily replace the `%wasm-note-startup-step` calls with C-level logging via a foreign call.

## Key Insight: Module Installation vs Symbol Binding

WASM modules are installed into the function table BEFORE cold-boot-init runs. **But** module installation only puts compiled code into the WASM table entries — it does NOT update Lisp symbol fcells. Symbol-to-code binding happens when FASLs are loaded (after cold-boot-init). So during cold-boot-init:

- All level-0 function entries ARE in the WASM table (entries 202-1406)
- All level-1 function entries ARE in the WASM table (entries 1407+)
- Level-0 symbol fcells ARE bound (set during boot image xload)
- **Level-1 symbol fcells are NOT bound** (still point to UDF sentinel)

This means any level-0 code that DYNAMICALLY calls a level-1 function (via symbol lookup, not direct entry) will fail with XFUNBND.

## What to Investigate

1. **Check the last WASM_STARTUP_STEP** in the build output to narrow the crash location
2. **Add temporary diagnostics** to `%run-cold-boot-init` to identify the exact failing cold-load function or operation
3. **Look at what `ASH` (entry 845) does** — specifically its const pool and what it tries to funcall. The const pool entry `s=1` at `val=0x0411df3e` is what was being accessed
4. **Check `*xload-cold-load-functions*`** — what functions are in this list, and do any of them call level-1 functions?
5. **Check `%resize-htab`** — does it call anything that could trigger an error on WASM?

## Architecture Summary

```
Build pipeline:
  make kernel → make subprims → boot image (level-0, 1110 modules) →
  runtime modules (level-1, 7557 modules) → root image (make-real-image.mjs)

Root image build sequence (make-real-image.mjs):
  1. Load boot image into WASM memory
  2. Install boot modules (entries 202-1406) into function table
  3. Install runtime modules (entries 1407+) into function table
  4. Install registry modules
  5. ★ Run cold-boot-init  ← CRASHES HERE
  6. Load level-1 FASLs (l1-boot-1, l1-boot-2, l1-boot-3, etc.)
  7. Save root.image

Calling convention:
  ARM throughout: arg_z = last (rightmost) param, TOS-based sync
```

## Critical Files

### Lisp (the crash site)
- `level-0/nfasload.lisp:1243` — `%run-cold-boot-init` definition (the function that crashes)
- `level-0/nfasload.lisp:1235` — `%wasm-note-startup-step` macro (diagnostic output)
- `level-1/l1-error-signal.lisp:19` — `%KERNEL-RESTART` definition (level-1, not available)
- `level-0/l0-hash.lisp` — `%resize-htab` and hash table operations
- `level-0/l0-misc.lisp` — `make-read-write-lock`, memory operations

### C kernel
- `lisp-kernel/wasm-kernel-stubs.c:3119` — `wasm_run_cold_boot_init()` C wrapper
- `lisp-kernel/wasm-subprims-provider.c` — subprims (funcall, error signaling)

### JS orchestration
- `scripts/wasm/lib/make-real-image.mjs:1028-1236` — module install + cold-boot-init + FASL load sequence
- `scripts/wasm/lib/ccl-loader.mjs:621-983` — `installCompiledModulesFromBundle`
- `scripts/wasm/lib/microkernel.mjs` — WASM runtime wrapper

### Diagnostics
- `scripts/wasm/lookup-entry.mjs` — resolve entry index to function name
- `scripts/wasm/check-freshness.sh` — verify build artifacts are aligned
- `scripts/wasm/check-lisp-syntax.sh` — paren check before rebuilding (uses CCL reader)
- `doc/wasm/debugging.md` — full debugging guide
- `doc/wasm/calling-convention-abi.md` — ABI spec

## Build & Test Commands

```bash
# Full rebuild (6+ minutes)
scripts/wasm/rebuild-everything.sh

# Verify artifacts are fresh before debugging
scripts/wasm/check-freshness.sh

# Check Lisp syntax after editing .lisp files
scripts/wasm/check-lisp-syntax.sh compiler/WASM/wasm2.lisp
scripts/wasm/check-lisp-syntax.sh --compiler --level0

# Look up entry index → function name
node scripts/wasm/lookup-entry.mjs 845

# Root image build only (skip kernel/module compile)
node --max-old-space-size=8192 scripts/wasm/lib/make-real-image.mjs \
  --output build/wasm32/images/root.image \
  --manifest-out build/wasm32/images/root.image.manifest.json \
  --modules build/wasm32/modules/wasm-runtime-modules.json \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json
```

## Suggested Approach

1. **Add C-level step logging** to `wasm_run_cold_boot_init()` in `lisp-kernel/wasm-kernel-stubs.c` — call `wasm_host_log` at key points, OR add C-level checkpoints that log via `wasm_debug_str`/`wasm_debug_uint` between the funcall and the throw check. The Lisp-level `%wasm-note-startup-step` output is invisible (Lisp stdout not connected to Node.js console).
2. **Add a handler-case/ignore-errors** wrapper around the cold-load-functions loop (step 40→50) in `%run-cold-boot-init` to see if cold-boot-init can complete when errors are suppressed
3. **Identify the exact operation** that triggers the error — is it a cold-load function, hash table resize, or binding index walk?
4. **Fix the root cause** — likely a WASM-specific issue in a level-0 function (wrong implementation, missing bridge function, or const pool reference error)
5. Do NOT try to make `%KERNEL-RESTART` available during cold-boot-init — native CCL doesn't have it either. Fix the error that triggers the error system.
