# WASM32 CCL Bootstrap & Real Image Pipeline (Design)

## Purpose
Design a **three‑step, wasm‑only** bootstrap pipeline that produces a real
WASM32 root image (`doc/wasm/root.image`) using best practices from CCL’s
existing xload backends (x86/arm/ppc). The plan is scoped to **WASM32 only**
and **must not change behavior on any other platform**.

This document is intended to be executable as a three‑step implementation
plan, in dependency order.

## Non‑Negotiable Constraints
- **WASM‑only changes**: all code changes must be gated by `#+wasm32-target`
  or be in new wasm‑specific files.
- **No changes to non‑WASM behavior**: shared files may be edited only under
  `#+wasm32-target` branches or by adding new wasm‑only module entries.
- **No UI work**: do not touch `web-ui/` (beyond existing JS runtime helpers).
- **Stage‑2 stepping baseline** remains the portable model.

## Current State (Summary)
- Kernel builds for wasm32 (freestanding) and runs with the JS microkernel.
- Minimal image loader works; real image policy script exists
  (`scripts/wasm/make-real-image.lisp`) but **requires a wasm32‑target CCL**.
- No wasm32 cross‑xload backend exists; no wasm boot image can be generated
  via `cross-xload-level-0`.
- WASM file I/O in `unix-calls.c` is **read‑only** (named blobs); `save-application`
  cannot write images.

## Dependencies & Best Practices (from existing backends)
### xload backends (xdump/*fasload.lisp)
Common structure across x86/arm/ppc:
- `make-backend-xload-info` with:
  - `:name` (target backend name)
  - `:macro-apply-code-function`, `:closure-trampoline-code`, `:udf-code`
  - `:default-image-name`, `:default-startup-file-name`
  - `:subdirs` for target‑specific level‑0 files
  - `:compiler-target-name` (must match backend name)
  - `:image-base-address`, `:purespace-reserve`, `:static-space-address`
  - `:nil-relative-symbols`
  - `:static-space-init-function`
- `add-xload-backend` called once per target.
- `*xload-default-backend*` set under target feature flags.

### Stub code patterns
Examples:
- x86‑64: macro‑apply and UDF use UUO stubs in a code vector.
- x86‑32: similar UUO, `closure-trampoline-code` can be nil.
- ARM: code vectors built via ARM LAP; explicit closure trampoline.

### Cross‑dump workflow
`xdump/xfasload.lisp` provides:
- `(cross-xload-level-0 target)` which uses a target xload backend
  plus target compiler backend to emit a boot image.

## Decision Points (Need Owner Input)
These choices affect the design. **Please decide** before implementation:

1. **WASM xload backend name & output path**
   - Option A (recommended): backend name `:wasm32`,
     default boot image path `ccl:ccl;wasm-boot.image`.
   - Option B: backend name `:wasm32`, output under `doc/wasm/wasm-boot.image`.

2. **Macro‑apply / UDF / closure trampoline representation**
   - Option A (recommended): **table‑index entrypoint** stubs implemented in the
     wasm kernel (or provider), and xload emits code vectors that are minimal
     “call‑indirect” shims targeting those entrypoints.
   - Option B: treat `%macro-code%` / `%closure-code%` as **non‑code** and
     set `*xload-target-use-code-vectors* = NIL` for wasm (requires careful audit
     of the compiler/runtime expectations).

3. **Save‑application output channel**
   - Option A (recommended): use existing `KERNEL_STREAM_KIND_FILE`
     + persistence service, and add a Node helper to **extract the saved file**
     from the persistence store and write `doc/wasm/root.image`.
   - Option B: implement a Node‑only FS backend for `persistenceService`
     (real host FS).
   - Option C: add new kernel_request opcode for “dump image to host”
     (ABI change; higher risk).

4. **Minimum file operations to support**
   - Option A (recommended): implement `open/read/write/close`, **plus**
     `lseek` and `ftruncate` for wasm (required by `save-application` paths).
   - Option B: emulate lseek/ftruncate at Lisp level with buffers (riskier,
     more intrusive).

5. **Level‑0 target sources for WASM**
   - Option A (recommended): add `level-0/WASM/` with wasm‑specific
     replacements for ARM LAP functions (small, explicit set), and point the
     wasm xload backend at that directory.
   - Option B: add `#+wasm32-target` branches inside `level-0/ARM/*.lisp` to
     provide wasm equivalents in‑place (risk of large diffs in ARM files).
   - Option C: attempt to reuse `level-0/ARM` unmodified (likely fails due to
     `defarmlapfunction` and ARM LAP usage).

## Step 1 — Add a WASM xload backend (foundational)
**Goal:** produce a wasm boot image via `(cross-xload-level-0 :wasm32)`.

### 1.1 New backend file
Add `xdump/xwasmfasload.lisp`:
- `require` the standard xload infrastructure:
  - `FASLENV`, `XFASLOAD`
- Use ARM‑layout values (WASM uses ARM layout):
  - `:nil-relative-symbols` → `arm::*arm-nil-relative-symbols*`
  - `:image-base-address` → match wasm image base (recommend `#x10000000`)
  - `:purespace-reserve` → similar to 32‑bit ARM (`(ash 64 20)` or `(ash 128 20)`)
  - `:static-space-address` → same formula used by ARM32 backends
- Provide `macro-apply`, `udf`, `closure` stubs (see Step 2).
- Use startup file name matching wasm target fasl:
  - wasm backend uses `:target-fasl-pathname` type `"lafsl"`
  - default startup file name: `level-1.lafsl`

### 1.2 Wire into build system (wasm‑only)
Edits in shared files must be **`#+wasm32-target` only**:
- `lib/systems.lisp`
  - add `xwasmfasload` module under `#+wasm32-target`.
- `lib/compile-ccl.lisp`
  - add wasm xload module list (e.g., `*wasm-xload-modules*`) under
    `#+wasm32-target` and include it in `target-xload-modules`.

### 1.3 Verification
From host CCL:
```lisp
(ccl:cross-xload-level-0 :wasm32)
```

### Step‑1 Deliverables
- `xdump/xwasmfasload.lisp`
- wasm‑only module wiring in `lib/systems.lisp` and `lib/compile-ccl.lisp`
- boot image written to the chosen location

## Step 2 — WASM stubs for macro‑apply / UDF / closure trampoline
**Goal:** xload produces valid function objects for wasm32 bring‑up.

### 2.1 Define stub strategy (depends on Decision #2)
This controls how `%macro-code%`, `%closure-code%`, and `%unbound-function%`
behave in wasm.

**Option A (recommended)**:
- Provide wasm‑native stub entrypoints (table indices) in the kernel or
  provider module (e.g., `wasm_macro_apply_stub`, `wasm_udf_stub`,
  `wasm_closure_trampoline_stub`).
- xload backend emits small code vectors or function objects that
  dispatch to these entrypoints. This keeps the “code‑vector” model intact.

**Option B**:
- If safe, make wasm target behave like “no code vectors” and set
  `*xload-target-use-code-vectors* = NIL` for wasm, and directly store
  fixnum entrypoint indices into `%macro-code%` / `%closure-code%`.
- Requires careful audit in `compiler/WASM/` and any runtime uses.

### 2.2 Kernel/provider additions (WASM only)
- Add new wasm exports for stub entrypoints (if Option A).
- Ensure these are installed in the subprims table before boot.

### 2.3 wasm‑xload backend uses these stubs
- `macro-apply-code-function` returns a code vector or fixnum entry index.
- `udf-code` and `closure-trampoline-code` similarly derived.

### 2.4 Verification
1. `cross-xload-level-0 :wasm32` produces boot image without errors.
2. Use `doc/wasm/js/load-image.mjs --start-lisp <boot-image>` and verify
   that the runtime enters Lisp without immediate macro‑apply/udf traps.

### Step‑2 Deliverables
- wasm stub entrypoints (kernel or provider)
- xload backend wired to those stubs
- a wasm boot image that can load level‑1 in wasm

## Step 3 — Save‑application output path (real image)
**Goal:** the wasm32 runtime can write `doc/wasm/root.image`.

### 3.1 Enable wasm write paths in `unix-calls.c` (WASM only)
- Extend `lisp_open` to support write flags:
  - map `O_RDONLY` → `KERNEL_STREAM_KIND_NAMED_RO` (existing)
  - map write flags (`O_WRONLY`, `O_RDWR`, `O_CREAT`, `O_TRUNC`, `O_APPEND`)
    to `KERNEL_STREAM_KIND_FILE` with a structured payload for `openFile`.
- Add `lisp_lseek` and `lisp_ftruncate` implementations:
  - either implement in microkernel file handles, or return `ENOSYS` only
    if verified unused by `save-application`.
- Ensure `lisp_close`, `lisp_read`, `lisp_write` remain routed through
  kernel_request (already implemented).

### 3.2 Enable delete/truncate support used by `save-application`
- `open-dumplisp-file` uses `%delete-file` and `probe-file`.
  Provide wasm‑only overrides for `%delete-file` (via `FS_DELETE`)
  and `%stat`/`%probe-file-x` if needed.
- If wasm filesystem is virtual, ensure the microkernel supports deletion.

### 3.3 Host extraction strategy (Decision #3)
- **Option A recommended**:
  - use `persistenceService` in‑memory or LMDB store;
  - add a Node helper to read the saved file from the VFS and write it to
    `doc/wasm/root.image`.
- **Option B**:
  - add a Node FS backend to persistence service that maps to host paths.

### 3.4 Reference Node helper
- `doc/wasm/js/make-root-image.mjs` (new):
  1. Instantiate kernel + microkernel with persistence service.
  2. Load boot image.
  3. `(save-application "/root.image")` inside wasm.
  4. Read bytes from persistence store and write `doc/wasm/root.image`.

### 3.5 Verification
- Run new helper and confirm `doc/wasm/root.image` created.
- Test with `node doc/wasm/js/load-image.mjs --start-lisp doc/wasm/root.image`.

### Step‑3 Deliverables
- wasm file‑write support in `unix-calls.c`
- microkernel persistence extraction path
- real root image produced

## Testing Strategy
- Unit: JS smoke tests (no UI) after each step.
- New smoke test(s):
  - `root-image-save-smoke.mjs` (optional) to verify the save path.
  - `root-image-start-smoke.mjs` to validate `wasm_ccl_start_lisp` using
    the real image.

## Risks & Mitigations
**Code‑vector assumptions**: wasm uses table indices; xload expects code vectors.
- Mitigation: Option A with kernel stubs and explicit code vectors.

**File semantics**: save-application may require `lseek/ftruncate`.
- Mitigation: implement seek/truncate in persistence service or emulate.

**ABI stability**: avoid new kernel_request opcodes unless necessary.
- Mitigation: use existing `STREAM_OPEN` kind FILE and VFS extraction.

## Implementation Plan (3 steps, strictly ordered)
1. **Step 1**: wasm xload backend + wiring.
2. **Step 2**: wasm stub entrypoints + code vector strategy.
3. **Step 3**: file output path + Node helper to emit `doc/wasm/root.image`.

---

## Decisions Needed (please choose)
1. Backend name + output path (Decision #1).
2. Stub representation (Decision #2).
3. Save‑application output channel (Decision #3).
4. Minimum file ops to implement (Decision #4).
