# CCL WASM: AI Assistant Guide

**Status:** Active
**Scope:** Operational context for AI coding assistants working on the CCL WASM port
**Last Updated:** 2026-02-16
**Doc Version:** 1.1.0

This document provides operational context for AI assistants working on the CCL WASM port. Read this first when starting a session to understand what works, what doesn't, and how to verify changes.

---

## Quick Context

**Project:** Clozure Common Lisp (CCL) port to WebAssembly
**Repository:** `/Users/buildsomething/Source/ccl`
**Branch:** `wasm-port`
**Status:** Early development / experimental
**Task Tracking:** `TODO.md` (root of repository)

**Critical Reading:**
- [README.md](README.md) - Current status (what works vs documented)
- [roadmap.md](roadmap.md) - Two-mode strategy (MVP-1, MVP-2)
- [project-overview.md](project-overview.md) - Architecture
- [build.md](build.md) - Build system
- [debugging.md](debugging.md) - Debugging tools and kernel state inspection (**read when troubleshooting**)

---

## Current Status (2026-02-16)

### What Works ✅
- **Build pipeline:** End-to-end functional (kernel → subprims → boot image → modules → root image attempt)
- **WASM kernel:** Compiles successfully (~1MB binary)
- **Subprims module:** Separate WASM module (`subprims.wasm`) with all `_SP*` implementations
- **Image loading:** Loads into memory, sections map correctly
- **RESTORE-LISP-POINTERS:** Called after image load, package hash tables rebuilt
- **Debugging infrastructure:** State dump fires on funcall errors and `_SPksignalerr`; JS TCR inspector; Chrome DevTools launcher
- **Boot image auto-build:** Triggered when missing during root image build
- **Environment:** Auto-detects macOS/Linux toolchain
- **Artifacts:** All outputs go to `build/wasm32/`

### Current Blocker ❌
- **FASL loading regression:** `level-1.lafsl` returns -72. Root cause: `%STRING-TO-STDERR` const pool contains `0x2c` (fixnum 11) where a function object for `LENGTH` should be. Investigation points to const pool encoding in `compiler/WASM/wasm2.lisp` (`wasm2-const-pool-entry` — `functionp` vs `xfunction` case).
- **Root image:** Build reaches FASL loading but fails due to above

### What Was Fixed (2026-02-16)
- ✅ `rebuild-everything.sh` now includes `subprims.wasm` rebuild (was missing — stale artifact caused silent failures)
- ✅ Debugging infrastructure: `wasm_debug_dump_state` rewritten without `snprintf %s` (unreliable); manual string helpers used instead
- ✅ State dump instrumented at `funcall-error` and `ksignalerr` in subprims module
- ✅ Spill stack leak on throw/catch fixed (`save_spill_sp` field added to catch frames)
- ✅ Character encoding bug fixed (`wasm_make_simple_base_string` memcpy)

### What Was Fixed (2026-02-15)
- ✅ RESTORE-LISP-POINTERS now called (was missing — root cause of -7 error)
- ✅ ~7000 lines dead code removed (instrumentation, startup binding map, startup truth)
- ✅ Build artifacts resolved (subprims.wasm, stale paths, missing exports)
- ✅ Boot image auto-build added

### Architecture (Two-Mode Strategy)

**MVP-1: Library/Embedded Mode** (current focus)
- Single runner, postMessage interface
- Works anywhere (no SharedArrayBuffer required)
- **BLOCKED** by compiled module installation (B2)

**MVP-2: Full Runtime Mode** (deferred)
- Multi-runner, SharedArrayBuffer required
- Secure context (HTTPS + COOP/COEP headers)
- web-ui/ide integration

---

## Build System

### Directory Structure

```
ccl/
├── build/wasm32/              # Build outputs (gitignored)
│   ├── kernel/wasmcl.wasm     # WASM kernel
│   ├── images/*.image         # Heap images
│   ├── modules/*.json         # Compiled modules
│   ├── subprims/subprims.wasm # Subprims provider
│   └── subprims-map.json      # Generated subprims table
├── lisp-kernel/wasm32/        # C kernel source
│   ├── Makefile               # Kernel build
│   └── config.mk              # Build defaults
├── scripts/wasm/              # Build scripts
│   ├── env.sh                 # Toolchain setup
│   ├── rebuild-everything.sh  # Full build orchestrator
│   ├── lib/                   # JS runtime libraries
│   │   ├── make-real-image.mjs  # Root image builder
│   │   ├── ccl-loader.mjs       # CCL loader
│   │   └── microkernel.mjs      # Microkernel
│   └── tests/                 # Smoke tests
├── doc/wasm/                  # Documentation ONLY (no artifacts)
│   └── *.md                   # Design docs
└── TODO.md                    # Task tracking
```

**IMPORTANT:** No build artifacts should ever be in `doc/` - only documentation files.

### Building

**Full rebuild (recommended):**
```bash
cd /Users/buildsomething/Source/ccl
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

**Kernel only:**
```bash
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32
```

**Subprims only** (after editing `wasm-subprims-provider.c`):
```bash
make -C lisp-kernel/wasm32/subprims clean all
```

**Clean:**
```bash
make -C lisp-kernel/wasm32 clean
make -C lisp-kernel/wasm32/subprims clean
rm -rf build/wasm32
```

---

## Testing

### Node.js Tests

**Run all smoke tests:**
```bash
cd /Users/buildsomething/Source/ccl
node scripts/wasm/tests/all-smoke.mjs
```

**Individual tests:**
```bash
node scripts/wasm/tests/kernel-request-smoke.mjs
node scripts/wasm/tests/compiler-smoke.mjs
node scripts/wasm/tests/smoke-test.mjs
```

**Common errors:**
- `ENOENT: no such file or directory` - Artifacts missing, run full build
- `Module not found` - Wrong working directory, must run from repo root

---

## Debugging

See [debugging.md](debugging.md) for comprehensive debugging workflows and tools.

**Quick reference for troubleshooting sessions:**

```bash
# Run root image build and capture state dumps
node scripts/wasm/lib/make-real-image.mjs \
  --output build/wasm32/images/root.image \
  --modules build/wasm32/modules/wasm-runtime-modules.json \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json 2>&1 | grep -A 25 "STATE DUMP"

# Interactive debugging with Chrome DevTools
scripts/wasm/debug-run.sh scripts/wasm/tests/smoke-test.mjs

# Static binary inspection
wasm-objdump -x build/wasm32/kernel/wasmcl.wasm
wasm-objdump -x build/wasm32/subprims/subprims.wasm
```

**Architecture note:** The runtime has two WASM modules. The **kernel** (`wasmcl.wasm`) handles memory, GC, image loading, const pools, debug dump. The **subprims** module (`subprims.wasm`) handles all `_SP*` functions including funcall dispatch, catch/throw, error signaling. Cross-module calls use WASM imports. Both must be rebuilt together.

**snprintf policy:** The kernel provides a hand-rolled `vsnprintf` (no libc linked). Use `snprintf` only for numeric formats (`%x`, `%u`, `%d`). The `%s` format is unreliable with width modifiers. For string output, use the manual helpers in `wasm-kernel-stubs.c` (`wasm_debug_str`, `wasm_debug_hex8`, `wasm_debug_uint`).

**C-side conditional trap:**
```c
if (suspicious_condition) {
  wasm_debug_dump_state("descriptive label");
  __builtin_trap();
}
```

---

## Critical Context

### Compiled Module Installation (CRITICAL BLOCKER)

**Problem:** 7555 of 7557 compiled modules are skipped during installation
**Impact:** Function table entries not populated, FASL loading traps
**Status:** Uninvestigated — next critical-path task
**Location:** See [TODO.md](../../TODO.md) blocker B2

### What Was Removed (2026-02-15)

**Startup binding map** — A 2,500+ line WASM-only workaround that does NOT exist on any native CCL platform (x86, ARM, PPC). It was compensating for a missing RESTORE-LISP-POINTERS call. Removed entirely:
- 6 source files deleted
- Build pipeline cleaned (compile-wasm-fasls.sh, rebuild-everything.sh, make-real-image.lisp, pack-inline-bundle-v2.mjs)
- make-real-image.mjs stripped from ~4800 to ~2300 lines

**Instrumentation** — ~2400 lines of C kernel debug code (wasm_emit_*, wasm_debug_*, startup truth, UI demo payloads) and ~2100 lines of JS/Lisp/shell references.

**Startup truth** — An end-to-end diagnostic feature (shell → JS → C → Lisp) fully retired.

### RESTORE-LISP-POINTERS (FIXED)

**What:** Every native CCL platform calls RESTORE-LISP-POINTERS after loading an image to rehash package hash tables. WASM was missing this call.

**Fix:** Added `wasm_restore_lisp_pointers()` kernel export. Called from make-real-image.mjs:
- **Early call** (after image load): Returns -3 for boot images (expected — function not yet defined)
- **Post-fasload call** (after FASLs loaded): Succeeds (rc=0)

### Character Encoding

**Design:** UTF-32 (CL internal) ↔ UTF-8 (wire) ↔ UTF-16 (JS internal)
**NOT ASCII-only:** Full Unicode support from day one

### Two-Mode Strategy

**DON'T SAY:** "replacement lane", "legacy lane", "ASCII-first", "ASCII-only"
**DO SAY:** "MVP-1 / Library Mode", "MVP-2 / Full Runtime Mode", "UTF-8 wire format"

---

## Session Start Protocol

1. Read `TODO.md` to understand current task status
2. Identify the highest-priority unblocked task
3. Ask user which task to work on (suggest the critical path task)
4. Use TodoWrite for micro-tracking within the session
5. Update TODO.md when tasks complete or new blockers discovered

---

## Quick Reference

### Key Commands

```bash
# Setup environment
source scripts/wasm/env.sh

# Full rebuild
scripts/wasm/rebuild-everything.sh

# Kernel only
make -C lisp-kernel/wasm32

# Run tests
node scripts/wasm/tests/all-smoke.mjs

# Clean
rm -rf build/wasm32
make -C lisp-kernel/wasm32 clean
```

### Key Files

- `TODO.md` - Task tracking and blockers
- `doc/wasm/README.md` - Status and navigation
- `doc/wasm/roadmap.md` - Strategy
- `doc/wasm/build.md` - Build system
- `scripts/wasm/lib/make-real-image.mjs` - Root image builder
- `scripts/wasm/rebuild-everything.sh` - Build orchestrator

---

## Documentation Standards

See [STYLE-GUIDE.md](STYLE-GUIDE.md) for full standards.

- ✅ **Working** - Actually implemented and tested
- ⚠️ **Partial** - Partially implemented, unstable
- ❌ **Not working** - Broken or not implemented
- ⏸️ **Deferred** - Designed but deferred to MVP-2

**Honesty:** Always distinguish "designed" vs "implemented" and "documented" vs "working."

---

## Related Documentation

- [README.md](README.md) – Current status and navigation
- [roadmap.md](roadmap.md) – Development strategy
- [build.md](build.md) – Build documentation
- [project-overview.md](project-overview.md) – Architecture overview
- [porting-status.md](porting-status.md) – Feature implementation status
- [STYLE-GUIDE.md](STYLE-GUIDE.md) – Documentation standards
