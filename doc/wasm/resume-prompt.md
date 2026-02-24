# CCL WASM32 Port — Session Resume Prompt

> Copy everything below the line into a new Claude Code session.

---

## Role & Project

You are resuming work on the **Clozure Common Lisp (CCL) WASM32 port**. Repository: `/Users/buildsomething/Source/ccl`, branch: `wasm-port`.

This is a port of a mature 32-bit Common Lisp implementation to WebAssembly. The architecture is:
- **C kernel** compiled to `wasmcl.wasm` (WASM32, no WASI — custom libc shim)
- **Subprims** compiled to `subprims.wasm` (separate module, linked at runtime)
- **Lisp compiler backend** cross-compiles from x86-64 host CCL to WASM32 target
- **Node.js orchestrator** (`make-real-image.mjs`) drives the full bootstrap pipeline
- **ARM32 is the reference architecture** — check `compiler/ARM/` when investigating compiler/runtime bugs

Read `CLAUDE.md` and `TODO.md` at the repo root before starting any work. They contain standing rules and the full bug-fix history.

## Current State (as of 2026-02-23)

### What Works (v46 build)
- Full bootstrap pipeline completes end-to-end:
  ```
  boot image load → 1103/1104 boot modules → 7557/7557 runtime modules
  → cold-boot-init (returns 0, startup-step=4131) → 38 FASL files → save-image
  ```
- Saved image: `build/wasm32/images/root.image` (2.3 GiB) with valid header + trailer
- Sanity check passes (saved image loads back into WASM kernel)
- Manifest: `build/wasm32/images/root.image.manifest.json`

### Current Blocker: FASL Loading
- `l1-cl-package.lafsl` (first FASL) fails with return code **-72**
- The FASL loader starts (prints `";Loading l1-fasls/l1-cl-package.lafsl"`) then hits a funcall-error
- Entry 1087 with `nfn=0x04000001` (likely GC-forwarded or stale function reference)
- This is the **frontier** — cold-boot-init is complete, FASL loading is the next phase
- See `doc/wasm/resume-fasl-loading-investigation.md` for detailed investigation notes

### Known Minor Issues
- Entry 975: WASM validation error (1 of 1104 boot modules fails compilation)
- `%save-application-internal` symbol not found — falls back to C `save_application` (works fine)
- `lisp_lseek` (unix-calls.c:228) still returns int32 for Lisp FFI consumers (only C `lseek` wrapper is fixed)
- 3 benign `_SPksignalerr` errors during cold-boot-init (absorbed by pending_throw guard)

### Uncommitted Changes (14 files modified)
Key files with uncommitted work:
- `lisp-kernel/image.c` — find_openmcl_image_file_header WASM32 fallback for >2 GiB images
- `lisp-kernel/wasm-no-wasi-libc.c` — 64-bit lseek via direct `wasm_kernel_stream_seek`
- `lisp-kernel/wasm-kernel-stubs.c` — save-image stubs, const pool installer
- `compiler/WASM/wasm2.lisp` — compiler backend fixes (temp local reuse, typecode, car/cdr, etc.)
- `scripts/wasm/lib/make-real-image.mjs` — image builder (trailer fixup, sha256, diagnostics)
- `scripts/wasm/lib/persist-service.mjs` — VFS buffer growth for >2 GiB
- `scripts/wasm/lib/microkernel.mjs` — OOM safety in STREAM_WRITE
- `scripts/wasm/lib/tcr-inspector.mjs` — GPR/vstack diagnostic inspector

## Architecture Quick Reference

### CCL Image Format (32-bit)
```
[header: 64 bytes] [section data: page-aligned] ... [trailer: 16 bytes]
  sig0='Open' sig1='MCLI' sig2='mage' sig3='File'
  trailer.delta = signed offset from EOF to header (int32 — wraps for >2 GiB)
```
Sections: nilreg, readonly, dynamic, managed_static, static_cons (5 total).

### WASM32 Tag System (3-bit fulltags)
```
0: fixnum (even)    4: fixnum (odd)
1: nil (subtag)     5: cons
2: nodeheader       6: misc (vectors, symbols, functions, etc.)
3: imm              7: immheader
```
- `fulltag_misc=6`: vectors, symbols, functions, istructs — header at `ptr - 6`
- `fulltag_cons=5`: cons cells — car at `ptr - 5 + 4`, cdr at `ptr - 5`
- Fixnums: value = `word >> 2` (2-bit fixnum tag, but 3-bit fulltag mask)

### Register Mapping (GPRs in TCR)
```
GPR[0]=rcontext  GPR[4]=arg_z   GPR[8]=temp1    GPR[12]=Rfn
GPR[1]=arg_x     GPR[5]=temp0   GPR[9]=temp2    GPR[13]=allocptr
GPR[2]=arg_y     GPR[6]=nargs   GPR[10]=vsp     GPR[14]=tsp
GPR[3]=imm0      GPR[7]=fn      GPR[11]=sp      GPR[15]=rcontext(dup)
```

### Key Build Commands
```bash
# Source the WASM environment (required for kernel builds)
source scripts/wasm/env.sh

# Rebuild just the C kernel (produces wasmcl.wasm) — ~2 minutes
make -C lisp-kernel/wasm32

# Full bootstrap pipeline (kernel + subprims + boot image + modules + root image) — ~40 minutes
scripts/wasm/rebuild-everything.sh

# Run just the image builder (requires pre-built kernel + modules)
node scripts/wasm/lib/make-real-image.mjs \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json

# Check if build artifacts are stale
scripts/wasm/check-freshness.sh

# Lookup a function table entry by index
node scripts/wasm/lookup-entry.mjs <index>
```

**CRITICAL:** Always pass `--boot-modules` when running `make-real-image.mjs` directly. Without it, level-0 functions (entries 0–~1400) are never installed and cold-boot-init crashes silently.

### Key File Map

**C Kernel** (lisp-kernel/):
| File | Purpose |
|------|---------|
| `pmcl-kernel.c` | Main entry, `wasm_ccl_load_image`, `wasm_ccl_start` |
| `image.c` | Image load/save, `find_openmcl_image_file_header`, `load_openmcl_image` |
| `wasm-no-wasi-libc.c` | Custom libc shim (lseek, read, write, open, etc.) |
| `wasm-kernel-stubs.c` | Kernel-side stubs (`wasm_save_image_direct`, `wasm_funcall_common`, const pool) |
| `wasm-kernel-imports.c` | WASM imports from JS host |
| `wasm-subprims.c` | Core subprimitive dispatch (`_SPfuncall`, `_SPmisc_ref`, etc.) |
| `wasm-ccl-step.c` | Single-step execution harness |
| `wasm-host.c` / `wasm-host.h` | Host bridge interface |
| `wasm-gc.c` | GC integration |
| `unix-calls.c` | Lisp FFI (`lisp_lseek` — returns int32, beware!) |
| `platform-wasm32.h` | Platform defines (`WASM32`, `PLATFORM=39`) |

**Compiler** (compiler/WASM/):
| File | Purpose |
|------|---------|
| `wasm-arch.lisp` | Architecture defs (registers, constants, struct layouts) |
| `wasm2.lisp` | Code generation (vinsns, prologue, calling convention) |
| `wasm-vinsns.lisp` | Virtual instruction definitions |
| `wasm-backend.lisp` | Backend driver |
| `wasm-ffi.lisp` | FFI layer |

**JS Orchestrator** (scripts/wasm/lib/):
| File | Purpose |
|------|---------|
| `make-real-image.mjs` | Full pipeline: boot → modules → cold-boot → FASL → save-image |
| `microkernel.mjs` | WASM runtime: memory, imports, request/response buffer |
| `ccl-loader.mjs` | Module installer (compiled WASM → function table) |
| `load-image.mjs` | Image loader + sanity checker |
| `persist-service.mjs` | Virtual filesystem for WASM I/O |
| `tcr-inspector.mjs` | TCR/GPR/vstack diagnostic dumper |
| `abi-constants.mjs` | Generated ABI constants (DO NOT edit — edit C headers) |

**Level-0 Lisp** (level-0/WASM/):
| File | Purpose |
|------|---------|
| `wasm-misc.lisp` | 61 fns: atomics, threading, memory, lock stubs |
| `wasm-utils.lisp` | 39 fns: GC, heap, area walking |
| `wasm-bignum.lisp` | 75 fns: bignum digit arithmetic |
| `wasm-float.lisp` | 48 fns: IEEE754 manipulation |
| `wasm-symbol.lisp` | 10 fns: symbol ops, `%pname-hash` |
| Others | `wasm-array`, `wasm-hash`, `wasm-numbers`, `wasm-clos`, `wasm-pred`, `wasm-io`, `wasm-def` |

## Bugs Fixed (Condensed History)

These are the major classes of bugs encountered and fixed. If you see similar symptoms, check this list before investigating from scratch:

1. **box_fixnum overflow (>1 GiB heap):** `box_fixnum(untag(ptr))` overflows i32 when ptr > 0x3FFFFFFF. Affected: `%car/%cdr`, `wasm2-typecode`, `%alloc-misc`. Fix pattern: pass tagged pointer directly + handle in `wasm_lisp_word_ref`.

2. **lseek int32 truncation (>2 GiB files):** `lisp_lseek` returns int32. `lseek` wrapper in `wasm-no-wasi-libc.c` now calls `wasm_kernel_stream_seek` directly with 64-bit types.

3. **Compiler temp local reuse:** `wasm2-ensure-temp-local` returns shared local 0. Multiple uses in same expression clobber each other. Fix: use `wasm2-allocate-temp` for unique locals.

4. **Arg register convention:** WASM follows ARM: `arg_z = last param`. Compiler prologue had missing `(reverse req)`. Some subprims follow ARM convention, others follow WASM convention — mixed.

5. **Cross-compilation target:: resolution:** `target::subtag-*` resolves to HOST (x86-64) at read time, not WASM target. Use `wasm::subtag-*` directly.

6. **Hash function overflow:** 32-bit unsigned arithmetic in `%pname-hash`/`%string-hash` overflows 30-bit fixnums. Rewrote with split hi16/lo16 accumulator.

7. **Subprims .rodata collision:** Both kernel and subprims used `--global-base=1024`. Fixed subprims to `--global-base=1064960`.

8. **Cold-boot error handling:** `catch_top=0x00000000` during cold-boot-init. Errors crash because no handler. Fix: `pending_throw(16)` + startup-step check.

## Debugging Workflow

1. **JS-only changes** (no rebuild needed): Edit files in `scripts/wasm/lib/`, re-run `node scripts/wasm/lib/make-real-image.mjs --boot-modules ...`
2. **C kernel changes** (rebuild needed, ~2 min): Edit `lisp-kernel/*.c`, run `make -C lisp-kernel/wasm32`, then re-run make-real-image
3. **Compiler changes** (full rebuild, ~40 min): Edit `compiler/WASM/*.lisp`, run `scripts/wasm/rebuild-everything.sh`
4. **Diagnostic tools:** `tcr-inspector.mjs` can dump GPRs, vstack, catch frames from JS catch handler in make-real-image.mjs

## What to Work on Next

The immediate blocker is **FASL loading**. The FASL dispatch table (`*fasl-dispatch-table*`) is valid (subtag 0xFA, 80 elements) but `fasldispatch` field of the faslstate reads wrong at runtime. Key investigation threads:

1. **faslstate.fasldispatch is slot 14** (0-indexed, because `()` entry in `def-accessors` consumes slot 0 for istruct-cell). Both read path (`wasm_lisp_word_ref`) and write path (`_SPmisc_set`) compute `tagged_ptr + 54` for slot 14. Static analysis says it's correct.

2. **The crash**: `_SPmisc_ref` traps because it gets a cons cell (fulltag 5) instead of the dispatch vector. The cons cell is at `arg_z=0x0027e8e5`.

3. **Hypothesis**: Runtime corruption — the slot was written correctly but something (GC? allocation? stack?) overwrites it. Need to dump the actual faslstate vector contents at crash time.

4. There is a plan file at `.claude/plans/refactored-leaping-raven.md` with a detailed JS-level diagnostic approach (dump faslstate, TCR GPRs, vstack scan) — review it but verify against current code state.

Ask the user what they want to focus on. Do not assume — the priority may have changed.
