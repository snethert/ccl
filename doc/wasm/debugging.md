# WASM Debugging Guide

**Status:** Active
**Scope:** Debugging tools, workflows, and kernel state inspection for the CCL WASM port
**Last Updated:** 2026-02-16
**Doc Version:** 1.1.0

## Purpose

Reference guide for debugging the CCL WASM kernel. Designed for rapid ingestion by AI assistants and human developers entering a troubleshooting session. Read this before adding ad-hoc logging — the tools described here are reusable and cover most debugging scenarios.

---

## Environment

### Toolchain

| Component | Value |
|-----------|-------|
| Compiler | clang 21.1.8 (LLVM, Homebrew) |
| Linker | wasm-ld (LLD) |
| Runtime | Node.js v25.6.0 |
| Compile flags | `-g` (DWARF embedded), `-O2` |
| Source maps | Not available (wasm-ld lacks `--source-map`) |
| Platform | macOS Darwin 24.6.0 (x86_64 host, wasm32 target) |

### Available Tools

| Tool | Installed | Purpose |
|------|-----------|---------|
| `wasm-objdump` | ✅ | Binary section inspection, function table, imports/exports |
| `wasm2wat` | ✅ | WASM → WAT text disassembly |
| `wasm-decompile` | ✅ | WASM → pseudo-C decompilation |
| `node --inspect-brk` | ✅ | Chrome DevTools with DWARF source-level stepping |
| Wasmtime | ❌ | Would enable GDB remote stub, but not installed |
| GDB/LLDB | ❌ for WASM | Cannot attach to WASM running inside Node.js |

### Constraints

- **GDB cannot debug WASM-in-Node.js.** GDB/LLDB debug native code only. The WASM engine is inside V8, inside Node — GDB sees V8's C++ internals, not WASM frames.
- **Wasmtime would support GDB** via its remote debug stub, but porting all JS host functions (microkernel, I/O, const pool) to Wasmtime's C/Rust API is a separate project.
- **Chrome DevTools is the only interactive WASM debugger** for our setup. It reads DWARF from the binary and shows C source.
- **All non-interactive debugging** goes through `wasm_host_log()` → stderr → captured by Node.js.
- **`snprintf` policy:** The kernel provides a hand-rolled `vsnprintf` in `wasm-no-wasi-libc.c` (no actual libc linked). The `%s` format is unreliable (fails with `%-8s` width modifiers). Use `snprintf` only for numeric formats (`%x`, `%u`, `%d`). For string content, use manual byte-copy helpers (`wasm_debug_str`, `wasm_debug_hex8`, `wasm_debug_uint` in `wasm-kernel-stubs.c`).

### Architecture: Kernel vs Subprims Module

The WASM runtime consists of two separate WASM modules, linked at instantiation by the JS host:

| Module | Source | Build | Purpose |
|--------|--------|-------|---------|
| **Kernel** (`wasmcl.wasm`) | `lisp-kernel/wasm-kernel-stubs.c` + 20 other C files | `make -C lisp-kernel/wasm32` | Memory management, GC, image loading, debug dump, spill stack, const pool install |
| **Subprims** (`subprims.wasm`) | `lisp-kernel/wasm-subprims-provider.c` | `make -C lisp-kernel/wasm32/subprims` | Function dispatch, catch/throw, error signaling, arithmetic, all `_SP*` subprims |

Cross-module calls use WASM imports. The subprims module imports kernel functions via:
```c
__attribute__((import_module("ccl"), import_name("wasm_debug_dump_state")))
void wasm_debug_dump_state(const char *label);
```

The kernel also contains stub implementations of all subprims (`wasm-subprims-standin.c`) that call `Bug()`. These stubs exist so the kernel links standalone; the JS host replaces them with the real subprims module implementations at instantiation via the shared function table.

**Build ordering matters:** `rebuild-everything.sh` builds kernel first, then subprims, then boot image, then compiled modules, then root image. All artifacts must be from the same build.

---

## TCR Memory Layout (WASM32)

The TCR (Thread Context Record) holds all per-thread state. On WASM32, all pointers and LispObj values are 4 bytes.

### Key Fields

Use `wasm_debug_tcr_offset(field_id)` to get exact byte offsets at runtime. The field IDs are:

| ID | Field | Type | Purpose |
|----|-------|------|---------|
| 0 | `wasm_gprs` | `LispObj[16]` | Simulated ARM registers (64 bytes total) |
| 1 | `wasm_spill_base` | `LispObj *` | Spill stack base (lowest valid address) |
| 2 | `wasm_spill_sp` | `LispObj *` | Spill stack pointer (current top) |
| 3 | `wasm_pending_throw` | `LispObj` | Non-zero when cooperative throw is in progress |
| 4 | `catch_top` | `LispObj` | Top of catch frame chain |
| 5 | `db_link` | `special_binding *` | Head of dynamic binding chain |
| 6 | `save_vsp` | `LispObj *` | VSP saved when in foreign code |
| 7 | `xframe` | `xframe_list *` | Exception frame linked list |
| 8 | `wasm_spill_limit` | `LispObj *` | Spill stack limit (highest valid address + 1) |
| 9 | `wasm_cstack_sp` | `void *` | C stack pointer |
| 10 | `nfp` | `void *` | Next frame pointer |

### GPR Register Map

The `wasm_gprs[16]` array simulates ARM registers:

| Index | Name | Purpose | GC-scanned |
|-------|------|---------|------------|
| 0 | imm0 | Immediate / scratch | No |
| 1 | imm1 | Immediate / scratch | No |
| 2 | nargs | Argument count (boxed fixnum) | No |
| 3 | rcontext | Context register | No |
| 4 | arg_z | First argument / return value | **Yes** |
| 5 | arg_y | Second argument | **Yes** |
| 6 | arg_x | Third argument | **Yes** |
| 7 | temp0 | Temporary | **Yes** |
| 8 | temp1 | Temporary | **Yes** |
| 9 | temp2/nfn | Current function (callee) | **Yes** |
| 10 | vsp | Value stack pointer | **Yes** |
| 11 | Rfn | Function object register | **Yes** |
| 12 | allocptr | Allocation pointer | No |
| 13 | Rsp | Stack pointer | No |
| 14 | Rlr | Link register (return address) | No |
| 15 | Rpc | Program counter | No |

**GC scans indices 4–11** (node registers). Indices 0–3 and 12–15 must never contain movable heap pointers.

### Spill Stack

The spill stack is a malloc'd heap area (128KB / 32K words) used to preserve WASM locals across import calls (subprim calls). It grows downward from `wasm_spill_limit`.

```
wasm_spill_base  ← lowest valid address
  ...
  [free space]
  ...
wasm_spill_sp    ← current top (values below here are live)
  [value N]
  [value N-1]
  ...
  [value 0]
wasm_spill_limit ← one past highest valid address (initial sp value)
```

**Key invariant:** `wasm_spill_base < wasm_spill_sp <= wasm_spill_limit`

GC scans from `wasm_spill_sp` to `wasm_spill_limit`. Values below `wasm_spill_sp` are dead.

### Catch Frame Structure

`wasm_catch_frame` (defined in `lisp-kernel/wasm-subprims-provider.c:13–25`):

| Offset | Field | Purpose |
|--------|-------|---------|
| +0 | header | Frame header with element count |
| +4 | link | Pointer to next catch frame |
| +8 | mvflag | Multiple-values flag |
| +12 | catch_tag | Catch tag (or `unbound_marker` for unwind-protect) |
| +16 | db_link | Dynamic binding chain at catch point |
| +20 | xframe | Exception frame at catch point |
| +24 | last_lisp_frame | Last lisp frame at catch point |
| +28 | nfp | Next frame pointer at catch point |
| +32 | save_vsp | Value stack pointer at catch point |
| +36 | cleanup_entry | Cleanup function entry (unwind-protect) |
| +40 | save_spill_sp | Spill stack pointer at catch point |

---

## Kernel State Dump (C-side)

### `wasm_debug_dump_state(label)`

**File:** `lisp-kernel/wasm-kernel-stubs.c`
**Export:** `wasm_debug_dump_state`

Dumps comprehensive TCR state to stderr via `wasm_host_log()`. Uses manual string helpers (`wasm_debug_hex8`, `wasm_debug_str`, `wasm_debug_uint`) — no `snprintf %s` (see Constraints).

```
=== STATE DUMP: funcall-error ===
  imm0     = 0x00000000
  imm1     = 0x000000b0
  nargs    = 0x00000004
  ...all 16 GPRs...
  spill: sp=0x0014e124 base=0x0012e490 limit=0x0014e490 depth=219
  catch_top=0x00000000 db_link=0x00000000 pending_throw=0x00000000
  VSP=0x0012dff4 top: 0x0407769e 0x0407769e 0x0406ff8e 0x00000000
  spill_push=1041 spill_pop=822
=== END STATE DUMP ===
```

**State dump sites** (fires automatically before error handling):

| Label | Location | Condition |
|-------|----------|-----------|
| `funcall-error` | `wasm-subprims-provider.c` (`wasm_signal_funcall_error`) | Any funcall dispatch error (bad fn value) — fires BEFORE registers are overwritten |
| `ksignalerr` | `wasm-subprims-provider.c` (`_SPksignalerr`) | Central error signaling — fires on all Lisp-level errors |
| `fn==nil` | `wasm-kernel-stubs.c` (`wasm_call_lisp_function`) | Function value is nil |
| `fn not misc` | `wasm-kernel-stubs.c` | Function value has wrong fulltag |
| `fcell not misc` | `wasm-kernel-stubs.c` | Symbol's function cell has wrong fulltag |
| `fn not function` | `wasm-kernel-stubs.c` | Object is not a function or pseudofunction |
| `entry not fixnum` | `wasm-kernel-stubs.c` | Entry index is not a fixnum |
| `nargs mismatch unary` | `wasm-kernel-stubs.c` | Unary ABI called with nargs != 1 |
| `nargs mismatch binary` | `wasm-kernel-stubs.c` | Binary ABI called with nargs != 2 |

**Callable from JS:** `kernel.instance.exports.wasm_debug_dump_state(0)` (null label → "?")

### `wasm_debug_tcr_offset(field_id)`

**File:** `lisp-kernel/wasm-kernel-stubs.c`
**Export:** `wasm_debug_tcr_offset`

Returns the byte offset of a TCR field from the TCR base pointer. Used by the JS inspector to discover struct layout at runtime (no hardcoded offsets).

```javascript
const gprs_offset = exports.wasm_debug_tcr_offset(0); // offset of wasm_gprs
```

---

## JS TCR Inspector

### `scripts/wasm/lib/tcr-inspector.mjs`

A JS module that reads TCR state directly from WASM linear memory via `DataView`. Discovers struct offsets at runtime via `wasm_debug_tcr_offset()`.

### API

```javascript
import { createInspector } from './tcr-inspector.mjs';
const inspect = createInspector(kernel.instance.exports, runtime.memory);
```

| Method | Purpose |
|--------|---------|
| `dumpGPRs()` | Print all 16 GPRs with names to stderr |
| `dumpSpillStack(depth)` | Print top N spill stack entries |
| `dumpVSP(depth)` | Print top N value stack entries |
| `dumpCatchFrames()` | Walk and print catch frame chain |
| `inspectObject(addr)` | Read object header, print type info |
| `snapshot()` | Return full state as JS object |
| `dumpAll()` | Call all dump methods |
| `getGPR(index)` | Read single GPR by index |
| `getField(name)` | Read TCR field by name |

### Usage: Post-Mortem After Trap

```javascript
try {
  kernel.instance.exports.wasm_ccl_step();
} catch (e) {
  if (e instanceof WebAssembly.RuntimeError) {
    console.error("Trap caught — inspecting state:");
    inspect.dumpAll();
  }
}
```

### Usage: Before/After Comparison

```javascript
const before = inspect.snapshot();
kernel.instance.exports.wasm_ccl_step();
const after = inspect.snapshot();
// Compare before.gprs.arg_z vs after.gprs.arg_z, etc.
```

---

## Debugging Workflows

### Workflow 1: Investigate a Trap (Most Common)

When a `RuntimeError: unreachable` occurs:

1. The trap was preceded by `wasm_debug_dump_state()` — check stderr
2. Search output for `=== STATE DUMP: <label> ===`
3. The label tells you which condition triggered
4. Read GPRs to understand what values were in play
5. Check `pending_throw` — non-zero means a cooperative throw was in flight
6. Check spill stack depth — non-zero at trap may indicate leaked spills

```bash
node scripts/wasm/tests/smoke-test.mjs 2>&1 | grep -A 25 "STATE DUMP"
```

### Workflow 2: Trap at a Specific Condition

To investigate a specific runtime condition:

1. Add a conditional check in the relevant C function:
   ```c
   if (some_condition) {
     wasm_debug_dump_state("descriptive label");
     __builtin_trap();
   }
   ```
2. Rebuild: `make -C lisp-kernel/wasm32` (kernel) and/or `make -C lisp-kernel/wasm32/subprims clean all` (subprims)
3. Run the test: `node <test>.mjs 2>&1 | tee debug.log`
4. Read the state dump in `debug.log`

### Workflow 3: Inspect State at Arbitrary JS Points

1. Import the inspector in your test script:
   ```javascript
   import { createInspector } from './tcr-inspector.mjs';
   ```
2. Create inspector after kernel instantiation:
   ```javascript
   const inspect = createInspector(kernel.instance.exports, runtime.memory);
   ```
3. Call `inspect.dumpAll()` or `inspect.snapshot()` at points of interest

### Workflow 4: Interactive Stepping (Chrome DevTools)

1. Run with the debug launcher:
   ```bash
   scripts/wasm/debug-run.sh scripts/wasm/tests/smoke-test.mjs
   ```
2. Open `chrome://inspect` in Chrome
3. Click "inspect" on the Node.js target that appears
4. Navigate to Sources → `wasm://` → find C source files (DWARF)
5. Set breakpoints, step through C code, inspect WASM locals

### Workflow 5: Static Binary Analysis

Inspect the compiled WASM binary without running it:

```bash
# List exports, imports, function table
wasm-objdump -x build/wasm32/kernel/wasmcl.wasm

# Full disassembly to WAT text format
wasm2wat build/wasm32/kernel/wasmcl.wasm -o kernel.wat

# Pseudo-C decompilation
wasm-decompile build/wasm32/kernel/wasmcl.wasm -o kernel.dcmp

# Search for a specific function in disassembly
wasm-objdump -d build/wasm32/kernel/wasmcl.wasm | grep -A 20 'wasm_call_lisp_function'
```

---

## Critical Code Paths

These are the code paths most likely to be involved in debugging. Know where they are and what they do.

### Function Dispatch

Two dispatch paths exist — one in each WASM module:

**Subprims module** (`wasm-subprims-provider.c`): `wasm_call_function_or_symbol()` — the primary dispatch. Called by `_SPfuncall`, `_SPjmpsym`, and all funcall helpers. Validates fn, resolves symbols, signals errors via `wasm_signal_funcall_error` → `_SPksignalerr`. State dumps fire at `funcall-error` and `ksignalerr` labels.

**Kernel module** (`wasm-kernel-stubs.c:126–201`): `wasm_call_lisp_function()` — secondary dispatch used by kernel-internal code (const pool installation, FASL loading). Has the same validation logic with `__builtin_trap()` at each check.

```
fn_value → check nil → check fulltag_misc
         → if symbol: resolve fcell → re-check fulltag
         → check subtag (function or pseudofunction)
         → set nfn + Rfn registers
         → extract entry index (must be fixnum)
         → look up GC policy mode and ABI kind
         → dispatch via ABI (unary_i32 / binary_i32 / legacy)
         → if !pending_throw: write result to arg_z
```

State dumps fire at every check point in both paths.

### Spill/Restore

**File:** `lisp-kernel/wasm-kernel-stubs.c:1591–1639`

- `wasm_spill_push(value)`: `*--sp = value; tcr->wasm_spill_sp = sp;`
- `wasm_spill_pop()`: `value = *sp++; tcr->wasm_spill_sp = sp; return value;`

Pure memory operations — no allocation, no GC trigger. The compiler wraps every subprim call with spill/restore of all spillable WASM locals.

The spill pop has a diagnostic check for value `0x2c` (logs push/pop counts and stack depth).

### Catch/Throw

**File:** `lisp-kernel/wasm-subprims-provider.c`

- `_SPmkcatch1v` / `_SPmkcatchmv`: Allocate `wasm_catch_frame` on C stack, save VSP, spill_sp, db_link, xframe, last_lisp_frame, nfp.
- `_SPnthrow1value` / `_SPnthrowvalues`: Cooperative unwind — set `pending_throw`, each function between throw and catch checks the flag and returns early. At the target catch frame, restore VSP and spill_sp.

**Key difference from ARM:** ARM uses `longjmp` which implicitly restores SP and frees all intermediate register save areas. WASM uses cooperative unwinding with explicit `save_spill_sp` restoration in catch frames.

### GC Root Scanning

**File:** `lisp-kernel/gc-common.c:688–697`

Scans `wasm_gprs[4..11]` (the node registers: arg_z through Rfn) and the spill stack from `wasm_spill_sp` to `wasm_spill_limit`.

**Safe invariant:** GC cannot trigger during a spill sequence because `wasm_spill_push` is pure memory operations (no allocation). Therefore, partially-spilled values (still in WASM locals) are never stale after GC.

---

## Common Failure Patterns

| Symptom | Likely Cause | First Steps |
|---------|-------------|-------------|
| `RuntimeError: unreachable` | `__builtin_trap()` fired | Read state dump label from stderr |
| fn is a small integer (e.g., 0x2c) | Const pool stored entry index instead of function object | Check const pool encoding in `wasm2.lisp` `wasm2-const-pool-entry`; verify tag 16 vs tag 4 encoding |
| Spill stack overflow (trap in push) | Leak during throw/catch cycles | Verify `save_spill_sp` is set in catch frames |
| Spill pop returns wrong value | Push/pop mismatch | Compare push and pop counts in state dump |
| GC moves object, WASM local stale | GC triggered during spill sequence | Should not happen — verify `wasm_spill_push` has no allocation |
| Wrong nargs at dispatch | nargs register not properly set | Check `wasm_gprs[2]` in state dump — should be boxed fixnum |
| `pending_throw` non-zero unexpectedly | Throw not consumed by catch | Walk catch frame chain, check catch_top |
| FASL loading returns -7 / -72 | Function not bound or const pool error | Check if the function's symbol has a valid fcell; check const pool installation for the failing entry |
| State dump shows `%-8s` for GPR names | `snprintf %s` unreliable in WASM | Use manual string helpers; do not use `snprintf` with `%s` format |
| State dump not firing on error | Error goes through subprims module, not kernel traps | Ensure `subprims.wasm` is rebuilt; check `wasm_signal_funcall_error` and `_SPksignalerr` have dump calls |

---

## Quick Reference

### Commands

```bash
# Build kernel (fast — C compilation only)
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32

# Build subprims module (must rebuild after editing wasm-subprims-provider.c)
make -C lisp-kernel/wasm32/subprims clean all

# Full rebuild (slow — kernel + subprims + boot + modules + root image)
scripts/wasm/rebuild-everything.sh

# Run smoke tests
node scripts/wasm/tests/all-smoke.mjs

# Debug with Chrome DevTools
scripts/wasm/debug-run.sh scripts/wasm/tests/smoke-test.mjs

# Static binary analysis
wasm-objdump -x build/wasm32/kernel/wasmcl.wasm
wasm2wat build/wasm32/kernel/wasmcl.wasm -o kernel.wat
```

### Key Files

| File | Module | Purpose |
|------|--------|---------|
| `lisp-kernel/wasm-kernel-stubs.c` | Kernel | Function dispatch, spill stack, debug dump, const pool install |
| `lisp-kernel/wasm-subprims-provider.c` | Subprims | Catch/throw, `_SPfuncall`, `_SPksignalerr`, all `_SP*` subprims |
| `lisp-kernel/wasm-subprims-standin.c` | Kernel | Stub subprims (call `Bug()`); overridden by subprims module at runtime |
| `lisp-kernel/wasm-no-wasi-libc.c` | Kernel | Hand-rolled libc (malloc, memset, vsnprintf); no actual libc linked |
| `lisp-kernel/gc-common.c` | Kernel | GC root scanning (including spill stack) |
| `lisp-kernel/arm-constants.h` | — | TCR structure, register indices, catch_frame |
| `compiler/WASM/wasm2.lisp` | — | Compiler backend — spill discipline, code generation, const pool encoding |
| `scripts/wasm/lib/tcr-inspector.mjs` | — | JS-side state inspector |
| `scripts/wasm/lib/ccl-loader.mjs` | — | WASM instantiation, import wiring, subprims table |
| `scripts/wasm/lib/microkernel.mjs` | — | Host-side kernel request dispatch |

---

## Related Documentation

- [ABI.md](ABI.md) – Calling conventions and register assignments
- [AI-ASSIST.md](AI-ASSIST.md) – AI session startup guide
- [build.md](build.md) – Build system and flags
- [testing.md](testing.md) – Test infrastructure
- [image-loader-spec.md](image-loader-spec.md) – Image loading and boot sequence
