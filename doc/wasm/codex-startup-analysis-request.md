# Codex Analysis Request: CCL WASM Startup Failures

**Scope: READ-ONLY ANALYSIS. Do NOT propose code changes. Do NOT write patches.**

You are being asked to analyze two startup failures in the CCL (Clozure Common Lisp) WASM32 port. Your job is to identify root causes and explain the failure chain. We will implement fixes ourselves.

---

## Repository

`ccl` — Clozure Common Lisp, branch `wasm-port`.

## Architecture Summary

The WASM port has a two-phase lifecycle:

1. **Build** (`make-real-image.mjs`): Instantiates the C kernel (`wasmcl.wasm`) and subprims (`subprims.wasm`) in Node.js, installs ~8675 compiled Lisp modules into a WebAssembly.Table, runs cold-boot-init, loads ~35 level-1 FASLs, patches critical symbol fcells, runs GC, and saves the Lisp heap as `root.image` (2.1 GiB). Also emits `startup-plan.json` (function table map) and `modules.bin` (merged WASM module binaries).

2. **Launch** (`load-image.mjs`): Reads `startup-plan.json`, loads `root.image` into WASM memory, compiles 36 merged module binaries, fills the function table, and calls `wasm_ccl_start_lisp()`.

Key invariant: **load-image.mjs does zero runtime scans.** All symbol resolution, const pool installation, and function binding happens at build time. The saved image is the truth.

---

## Failure 1: cold-boot-init regression during build

### Symptom

`make-real-image.mjs` fails at `wasm_run_cold_boot_init` with return code -6:

```
=== STATE DUMP: funcall-error ===
  nfn      = 0x0412d88e
  Rfn      = 0x0412d88e
  allocptr = 0x00000000
  spill: depth=0
  catch_top=0x00000000 db_link=0x00000000 pending_throw=0x00000000

funcall-err: code=13 (XNOFUN)
  errcode=0x00000000 datum=0x00000034 ft=4
  expected=0x0412d88e ft=6
  arg_z: subtag=0x2a (subtag_function)

ksignalerr: absorbed=1 calls=1

cold-boot-init: pending_throw=0x00000040 startup-step=0
cold-boot-init: threw (infra incomplete)
FAIL: wasm_run_cold_boot_init returned -6
```

### Context

- This is **deterministically reproducible** (failed twice in a row).
- The **exact same build inputs** (kernel, subprims, boot image, runtime modules) produced a successful build in the immediately preceding session.
- The only code change between success and failure is in `make-real-image.mjs` — the "invariant gate" section was moved from BEFORE the GC to AFTER the GC. This code runs ~500 lines AFTER cold-boot-init in the script. The cold-boot-init code path is byte-identical between the working and failing versions.
- `cold-boot-init: startup-step=0` means `%RUN-COLD-BOOT-INIT` threw at the very first step before incrementing `*WASM-STARTUP-STEP*`.
- `catch_top=0x00000000` — no catch frame is established before calling `%RUN-COLD-BOOT-INIT`.
- `allocptr=0x00000000` — allocation pointer is not initialized (this is the `wasm_gprs[12]` register, not `tcr->save_allocptr`).

### Key files to read

- `lisp-kernel/wasm-kernel-stubs.c` — `wasm_run_cold_boot_init()` (line ~3558), `start_lisp()` (line ~3300), `wasm_toplevel_loop()` (line ~650)
- `lisp-kernel/wasm-subprims-provider.c` — `_SPfuncall` dispatch, `wasm_call_function_value()`, `wasm_call_function_or_symbol()`, `_SPksignalerr()`
- `level-0/nfasload.lisp` — `%run-cold-boot-init` definition (line ~1243)
- `scripts/wasm/lib/make-real-image.mjs` — build pipeline, module installation, cold-boot-init call

### Questions to answer

1. What function is `%RUN-COLD-BOOT-INIT` trying to call at step 0 that triggers XNOFUN?
2. Why does the same build succeed in one session and fail deterministically in the next, given identical inputs?
3. Is there non-determinism in module installation (entry index assignment) that could cause a function table entry to be missing or wrong?
4. Could `allocptr=0` (the GPR register, not `tcr->save_allocptr`) cause the failure? Does compiled Lisp code read `wasm_gprs[allocptr]` during cold-boot-init?
5. Is the `catch_top=0` + `pending_throw` absorption masking a different root cause?

---

## Failure 2: startup funcall-error after successful build

### Symptom

When `load-image.mjs` loads a successfully-built `root.image` and calls `wasm_ccl_start_lisp()`, the toplevel loop hits funcall errors:

```
TL: MKCATCH1V
TL: FUNCALL nfn=0x878bf0d6 e=000019ad

funcall-err: code=13 sym=RUNTIME-BRIDGE-PUMP-COMMANDS  fcell=0x00294996
funcall-err: code=13 sym=%ERR-DISP                      fcell=0x002949a6
```

### Root cause (already identified, included for completeness)

During the build, the "invariant gate" allocated function objects for these two symbols using C `malloc` (via the kernel's exported `malloc`). C malloc allocates from the system heap, which is OUTSIDE the Lisp heap areas (nilreg, readonly, dynamic, managed-static, static-cons). The image save (`wasm_save_image_direct`) only serializes Lisp heap areas. So the malloc'd function objects are lost, and the fcell pointers dangle.

### Fix in progress

Move the invariant gate to after the pre-toplfunc GC and use `wasm_set_symbol_function_entry()` (which allocates via `wasm_misc_alloc` in the Lisp heap) instead of JS-side `malloc`. But this fix is blocked by Failure 1 (cold-boot-init regression).

### Questions to answer

1. Confirm or refute the root cause analysis: are C-malloc'd objects definitely outside the serialized heap areas?
2. Are there other symbols besides `RUNTIME-BRIDGE-PUMP-COMMANDS` and `%ERR-DISP` that might have the same problem (fcell pointing to malloc'd memory)?
3. After fixing the fcell issue, what other obstacles might prevent `toplevel-loop` from reaching the REPL?

---

## Additional context

### The pending_throw mechanism

WASM has no `longjmp`/`setjmp`. The WASM port uses `tcr->wasm_pending_throw` as a cooperative error propagation flag. When an error occurs with `catch_top=0` (no Lisp catch frame), `_SPksignalerr` absorbs the error by setting `pending_throw` and returning. Callers check `pending_throw` before continuing.

Recent fixes added pending_throw pre-checks to:
- `wasm_call_function_value` (entry)
- `wasm_call_function_or_symbol` (entry)
- `_SPksignalerr` (entry — skip if already throwing)
- `_SPksignalerr` (exit — unconditional clear after ERRDISP returns)

### Build pipeline order in make-real-image.mjs

1. Load kernel + subprims WASM
2. Create shared memory + function table
3. Install boot modules (~830 entries)
4. Install runtime modules (~7560 entries, ~40 minutes)
5. Set `wasm_subprims_ready(1)`
6. `wasm_run_cold_boot_init()` ← **Failure 1 here**
7. Load ~35 level-1 FASLs via `wasm_fasload_path()`
8. Image fixup scan (rebind symbols to correct entry indices)
9. Force-rebind phase
10. ~~JS invariant gate~~ (removed — was allocating via C malloc)
11. `wasm_reset_root_image_runtime_state()`
12. Pre-toplfunc GC (frees ~1.78 GB)
13. **NEW: kernel-based invariant gate** (uses `wasm_set_symbol_function_entry`)
14. `wasm_set_toplfunc_entry()`
15. Pre-save GC
16. `wasm_save_image_direct()` → root.image
17. Emit startup-plan.json + modules.bin

### NRS symbols referenced

- `%RUN-COLD-BOOT-INIT` — CCL package, runs infrastructure setup (locks, class cells, packages)
- `RUNTIME-BRIDGE-PUMP-COMMANDS` — CCL package, called on every REPL iteration to poll host commands
- `%ERR-DISP` — CCL package, the condition/error dispatcher
- `%TOPLEVEL-FUNCTION%` — NRS symbol 16, the toplevel function set by `wasm_set_toplfunc_entry`
- `RESTORE-LISP-POINTERS` — NRS symbol, called at startup to rehash package tables

---

**Deliverable: A written analysis of both failures. Root causes, failure chains, and any interactions between them. No code.**
