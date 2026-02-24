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

## Current State (as of 2026-02-24)

### What Works

The full bootstrap pipeline now completes end-to-end:
```
boot image load → 1107 boot modules (entries 202-1403)
→ 7555/7557 runtime modules (entries 1404-8958, 2 skipped as boot overlap)
→ cold-boot-init (returns 0, startup-step=4131)
→ 38 FASL files loaded (l1-cl-package through dumplisp)
→ save-image (2.3 GiB root.image)
```

**Test-boot results:**
| Mode | Result | Notes |
|------|--------|-------|
| `boot-only` | **rc=0** | Image loads, IPC protocol validation passes |
| `start-lisp` | **rc=0** | Lisp toplevel entered successfully |
| `run-toplevel` | **not yet tested** | Next step for REPL verification |

### MVP-1 Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 0A: LAP Bridge Functions | DONE | 333 defuns across 12 files |
| 0AA: Unit Tests | UNBLOCKED | 144 tests compiled; runtime blocked on FASL is now resolved |
| 0B: Zero-Relocation Image | DONE | image-base = __heap_base |
| **1: Verified Build** | **DONE** | All fasls load, image saves, test-boot passes |
| **2: Build-Time Completeness** | **NEXT** | const pool preinstall, startup-plan.json, modules.bin |
| 3: Deterministic Launcher | TODO | Delete ~2800 lines JS, REPL functional |

### Known Issues (non-blocking)

1. **MAKE-UARRAY-1 undefined:** funcall-error during `start-lisp` at entry 6665. Absorbed by error handler, does not prevent rc=0 return. Likely a level-1 function that should be defined but isn't being found.

2. **%save-application-internal not found:** Falls back to C `save_application` path (works fine).

3. **5 absorbed errors during cold-boot-init:** All with `catch_top=0x00000000` — benign type checks after useful work is done. See TODO.md for details.

4. **2 merged module batches fail WASM validation:** Fall back to individual modules. 7557/7557 end up installed.

5. **Entry 975:** 1 of 1107 boot modules fails WASM compilation (import type mismatch).

### Ramdisk

Build artifacts live on a macOS RAM disk at `/Volumes/CCLBuild` (symlinked from `build/wasm32`). **Does not survive reboot.** To recreate:
```bash
scripts/wasm/ramdisk.sh create 10240   # 10 GB
scripts/wasm/rebuild-everything.sh     # ~20 min full rebuild
```

After ramdisk recreation, also regenerate subprims artifacts:
```bash
python3 scripts/wasm/generate_subprims_artifacts.py
```

And copy kernel/subprims to lib/ for test-booting:
```bash
cp build/wasm32/kernel/wasmcl.wasm scripts/wasm/lib/wasmcl.wasm
cp build/wasm32/subprims/subprims.wasm scripts/wasm/lib/subprims.wasm
```

## Major Bugs Fixed (recent sessions)

### 1. Entry Index Collision (funcall-depth-exceeded) — commit d9ac4470

Boot image level-0 functions occupied entries 202-1403, but the runtime bundle was compiled with `start-entry-index=300`, overlapping entries 300-1403 with unrelated level-1 code. Caused infinite mutual recursion (FIND-CLASS-CELL ↔ NON-STANDARD-INSTANCE-CLASS-WRAPPER). Fix:
- `excludeEntries` parameter in `installCompiledModulesFromBundle`
- Boot entry indices collected and passed to runtime installation
- Runtime modules now start at entry 1404

### 2. Catch Frame Alignment (nthrow1value unreachable) — commit d9ac4470

`wasm_catch_frame` was 44 bytes (11 slots), not a multiple of 8. On dnode-aligned stack, `cf + fulltag_misc` produced tag 2 (nodeheader) instead of 6 (misc). All field reads shifted by one slot — `save_vsp` read `cleanup_entry` (NULL) → unreachable trap. Fix: added `LispObj _pad` field (48 bytes = 12 slots) + `_Static_assert`. File: `lisp-kernel/wasm-subprims-provider.c`.

### 3. FASL Loading (-72 return) — commit d9ac4470

Root cause was the catch frame alignment bug above + missing catch frame in `wasm_fasload_path`. The C wrapper now establishes a catch frame with `*TOPLEVEL-CATCH*` tag before calling `%FASLOAD`, and detects catch consumption on return.

### Historical Bug Pattern Reference

See TODO.md for the full list. Key recurring patterns:
- **box_fixnum overflow (>1 GiB heap):** pass tagged pointer directly
- **Compiler temp local reuse:** use `wasm2-allocate-temp` not `wasm2-ensure-temp-local`
- **Cross-compilation target:: resolution:** use `wasm::subtag-*` not `target::subtag-*`
- **Hash function overflow:** split hi16/lo16 accumulator for fixnum safety
- **Cold-boot error handling:** `pending_throw(16)` + startup-step check

## Architecture Quick Reference

### WASM32 Tag System (3-bit fulltags, from arm-constants.h)
```
0: fixnum (even)    4: fixnum (odd)
1: nil              5: cons
2: nodeheader       6: misc (vectors, symbols, functions, istructs)
3: imm              7: immheader
```
- nil_value = 0x04000001
- Fixnums: value = word >> 2

### Register Mapping (GPRs in TCR)
```
GPR[0]=imm0      GPR[4]=arg_z   GPR[8]=temp0    GPR[12]=allocptr
GPR[1]=imm1      GPR[5]=temp1   GPR[9]=nfn      GPR[13]=Rsp
GPR[2]=nargs     GPR[6]=fn      GPR[10]=vsp     GPR[14]=Rlr
GPR[3]=rctx      GPR[7]=Rfn                     GPR[15]=Rpc
```

### Key Build Commands
```bash
# Full rebuild (kernel + subprims + boot image + modules + root image) — ~20 min
scripts/wasm/rebuild-everything.sh

# Kernel only (~10 sec)
make -C lisp-kernel/wasm32

# Subprims only (~5 sec)
make -C lisp-kernel/wasm32/subprims clean all

# Root image only (requires pre-built kernel + modules)
node --max-old-space-size=8192 scripts/wasm/lib/make-real-image.mjs \
  --output build/wasm32/images/root.image \
  --modules build/wasm32/modules/wasm-runtime-modules.json \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json

# Test-boot
node scripts/wasm/lib/load-image.mjs --mode boot-only build/wasm32/images/root.image
node scripts/wasm/lib/load-image.mjs --mode start-lisp build/wasm32/images/root.image

# Check for stale artifacts
scripts/wasm/check-freshness.sh
```

**CRITICAL:** Always pass `--boot-modules` when running `make-real-image.mjs` directly.

### Key File Map

**C Kernel** (lisp-kernel/):
| File | Purpose |
|------|---------|
| `wasm-kernel-stubs.c` | `wasm_fasload_path`, `wasm_run_cold_boot_init`, const pool, save-image |
| `wasm-subprims-provider.c` | Subprims: funcall, catch/throw, error handling, `wasm_catch_frame` struct |
| `pmcl-kernel.c` | Main entry, `wasm_ccl_load_image` |
| `image.c` | Image load/save |
| `wasm-no-wasi-libc.c` | Custom libc shim |

**Compiler** (compiler/WASM/):
| File | Purpose |
|------|---------|
| `wasm2.lisp` | Code generation (vinsns, prologue, calling convention) |
| `wasm-arch.lisp` | Architecture defs (registers, constants, struct layouts) |

**JS Orchestrator** (scripts/wasm/lib/):
| File | Purpose |
|------|---------|
| `make-real-image.mjs` | Full pipeline: boot → modules → cold-boot → FASL → save-image |
| `load-image.mjs` | Image loader + test-boot |
| `ccl-loader.mjs` | Module installer (compiled WASM → function table) |
| `microkernel.mjs` | WASM runtime: memory, imports, request/response buffer |

**Level-0 Lisp** (level-0/WASM/): 12 files, 333 bridge functions

## What to Work on Next

Phase 1 is complete. The system builds and boots. The MVP-1 plan in [TODO.md](../../TODO.md) says:

**Phase 2: Build-Time Completeness + Launch Artifacts**
- [ ] Proactive const pool installation (all pools installed before image save)
- [ ] `startup-plan.json` emitted (flat function table map)
- [ ] `modules.bin` emitted (uncompressed concatenated WASM modules)

**Phase 3: Deterministic Launcher**
- [ ] DELETE `bootstrap-contract.mjs` (163 lines)
- [ ] DELETE `bootstrap-function-resolver.mjs` (975 lines)
- [ ] REWRITE `load-image.mjs` (1093 → ~200 lines)
- [ ] SIMPLIFY `ccl-loader.mjs` (keep only runtime dynamic compilation)
- [ ] REPL functional

**Or:** investigate the `MAKE-UARRAY-1` undefined function error to see if it blocks `run-toplevel` mode.

**Or:** run the Phase 0AA unit tests (144 bridge function tests) now that FASL loading works.

Ask the user what they want to focus on. Do not assume — the priority may have changed.
