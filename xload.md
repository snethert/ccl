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

## Current State (Summary, as of 2026-02-07)
- Kernel builds for wasm32 (freestanding) and runs with the JS microkernel.
- Minimal image loader works; real image policy script exists
  (`scripts/wasm/make-real-image.lisp`). The script injects `:wasm32-target`
  into `*features*` if missing, so a normal 64‑bit host CCL is sufficient;
  the Node helper path exists but is not adopted.
- A wasm32 xload backend exists and is wired (`xdump/xwasmfasload.lisp`,
  `lib/systems.lisp`, `lib/compile-ccl.lisp`), and
  `cross-xload-level-0 :wasm32` now completes and writes
  `ccl:ccl;wasm-boot.image`.
- Boot image build wrappers exist (`scripts/wasm/build-wasm-boot.lisp`,
  `scripts/wasm/build-wasm-boot.sh`).
- WASM fasl compilation is unblocked by wasm‑only stubs for OS/FFI paths
  (primarily in `level-1/linux-files.lisp`); re‑run
  `scripts/wasm/compile-wasm-fasls.sh` to confirm on the current tree.
- WASM file I/O in `unix-calls.c` is **read‑only** (named blobs); `save-application`
  cannot write images.
- `xdump/xfasload.lisp` now converts wasm u32 stub code vectors into target
  code vectors during image build, and lazily loads
  `ccl:xdump;heap-image.lisp` if `write-image-file` is not already present
  (so xfasload can always emit the boot image).

## Recent Design Changes (Since Last Revision)
- `compiler/WASM/wasm2.lisp` now builds lfuns with a 5‑slot layout
  (entry, codevector stub, const/keyvec, name, lfun‑bits) so xfasload sees
  valid symbol/codevector pairs; closures use `%closure-code%` as the
  codevector stub and keep the underlying lfun in slot 2.
- `level-1/linux-files.lisp` has wasm‑only stubs for filesystem, FFI, and
  process APIs to keep wasm fasl compilation from pulling in OS dependencies.
- `xdump/xfasload.lisp` now tries to include the ARM package when available
  and loads ARM arch macros in wasm cross‑load paths.
- `xdump/xfasload.lisp` now handles wasm stub code vectors and ensures
  `write-image-file` is available by loading `ccl:xdump;heap-image.lisp` if
  needed.

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

## Decisions (Resolved / Deferred)

### Resolved
1. **WASM xload backend name & output path:** backend name `:wasm32`,
   default boot image path `ccl:ccl;wasm-boot.image` (resolves to
   repo root `wasm-boot.image` via `scripts/wasm/build-wasm-boot.lisp`).
2. **Macro‑apply / UDF / closure trampoline representation:** table‑index
   entrypoint stubs; xload emits 1‑word code vectors containing fixnum table
   indices.
3. **Level‑0 target sources for WASM:** `level-0/WASM/` with wasm‑specific
   overrides; wasm xload backend points at that directory.

### Deferred (only needed for a wasm‑only save path)
1. **Save‑application output channel:** keep the host‑CCL path for now;
   Node helper extraction is optional future work.
2. **Minimum file operations to support:** likely `open/read/write/close`
   plus `lseek` and `ftruncate` if we implement wasm‑only `save-application`.

## Step 1 — Add a WASM xload backend (foundational)
**Goal:** produce a wasm boot image via `(cross-xload-level-0 :wasm32)`.
**Status:** Implemented and verified. `cross-xload-level-0 :wasm32` now
completes and writes `ccl:ccl;wasm-boot.image`. Rebuild
`xdump/xfasload.dx64fsl` after editing `xdump/xfasload.lisp`.

### 1.1 New backend file
Implemented in `xdump/xwasmfasload.lisp`:
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
  - `xwasmfasload` module under `#+wasm32-target`.
- `lib/compile-ccl.lisp`
  - `*wasm-xload-modules*` and `*wasm-compiler-backend-modules*` under
    `#+wasm32-target`, included in `target-xload-modules`.
- `level-0/WASM/wasm-def.lisp`
  - wasm‑only level‑0 overrides (`%fix-fn-entrypoint`, `macptr->fixnum`).

### 1.3 Verification
Use the wrapper:
`scripts/wasm/build-wasm-boot.sh` (drives `scripts/wasm/build-wasm-boot.lisp`).
Or from host CCL:
```lisp
(ccl:cross-xload-level-0 :wasm32)
```

### Step‑1 Deliverables
- `xdump/xwasmfasload.lisp`
- wasm‑only module wiring in `lib/systems.lisp` and `lib/compile-ccl.lisp`
- `level-0/WASM/wasm-def.lisp`
- build wrapper `scripts/wasm/build-wasm-boot.{lisp,sh}`
- boot image written to `ccl:ccl;wasm-boot.image` (repo root `wasm-boot.image`)

## Step 2 — WASM stubs for macro‑apply / UDF / closure trampoline
**Goal:** xload produces valid function objects for wasm32 bring‑up.
**Status:** Implemented; boot image build verifies the stub code‑vector path.
Runtime validation in the JS loader remains to be confirmed.

### 2.1 Stub strategy (chosen: Option A)
This controls how `%macro-code%`, `%closure-code%`, and `%unbound-function%`
behave in wasm.

**Option A (chosen)**:
- Stub entrypoints are table indices implemented in the subprims provider:
  `_SPwasm_macro_apply_stub` (index 130), `_SPwasm_udf_stub` (index 131), and
  `_SPcall_closure` (index 71 for the closure trampoline).
- xload emits 1‑word code vectors that contain the fixnum table index
  (see `xdump/xwasmfasload.lisp`), keeping the “code‑vector” model intact.

**Option B (not chosen)**:
- If safe, make wasm target behave like “no code vectors” and set
  `*xload-target-use-code-vectors* = NIL` for wasm, and directly store
  fixnum entrypoint indices into `%macro-code%` / `%closure-code%`.
- Requires careful audit in `compiler/WASM/` and any runtime uses.

### 2.2 Kernel/provider additions (WASM only)
- Stub entrypoints are implemented in `lisp-kernel/wasm-subprims-provider.c`.
- `doc/wasm/subprims-map.json` includes `_SPwasm_macro_apply_stub` and
  `_SPwasm_udf_stub` (generated via `scripts/wasm/generate_subprims_artifacts.py`).
- Keep the entry indices in `xdump/xwasmfasload.lisp` in sync with the map.

### 2.3 wasm‑xload backend uses these stubs
- `macro-apply-code-function` returns a 1‑word code vector containing the
  fixnum entry index.
- `udf-code` and `closure-trampoline-code` follow the same pattern.

### 2.4 Compiler/lfun alignment (WASM only)
- `compiler/WASM/wasm2.lisp` now builds lfuns with the 5‑slot layout that
  xfasload expects (entry, codevector stub, const/keyvec, name, lfun‑bits).
- `wasm2-set-afunc-lfun` stores the function name and codevector stub; closures
  use `%closure-code%` as the stub codevector and keep the underlying lfun
  in slot 2.

### 2.5 Verification
1. `cross-xload-level-0 :wasm32` produces a boot image without errors.
2. Use `doc/wasm/js/load-image.mjs --start-lisp BOOT_IMAGE_PATH` and verify
   that the runtime enters Lisp without immediate macro‑apply/udf traps.

### Step‑2 Deliverables
- wasm stub entrypoints in `lisp-kernel/wasm-subprims-provider.c`
- `doc/wasm/subprims-map.json` updated with stub entries
- xload backend wired to those stubs
- wasm compiler lfun layout matches xfasload expectations (`compiler/WASM/wasm2.lisp`)
- a wasm boot image that can load level‑1 in wasm

## Step 3 — Save‑application output path (real image)
**Goal:** the wasm32 runtime can write `doc/wasm/root.image` (optional if you
are generating the image from a host CCL today; required for a wasm‑only path).
**Status:** Deferred; current bring‑up uses host CCL +
`scripts/wasm/make-real-image.lisp` (no Node helper).

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

### 3.3 Host extraction strategy (deferred)
- Current path: host CCL + `scripts/wasm/make-real-image.lisp` writes
  `doc/wasm/root.image` directly.
- If a wasm‑only save path is needed later, choose between:
  - `persistenceService` + Node helper extraction, or
  - a Node FS backend for `persistenceService`.

### 3.4 Reference Node helper (optional)
- `doc/wasm/js/make-real-image.mjs`:
  1. Instantiate kernel + microkernel with persistence service.
  2. Load boot image.
  3. Load and run `scripts/wasm/make-real-image.lisp` inside wasm.
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

## Key Files & Commands
- `xdump/xwasmfasload.lisp` — wasm xload backend; stub entry indices.
- `xdump/xfasload.lisp` — cross‑xload driver; handles ARM package + wasm stub
  code vectors; loads `heap-image.lisp` for `write-image-file` when needed.
- `xdump/xfasload.dx64fsl` — compiled xfasload used by host CCL.
- `compiler/WASM/wasm-arch.lisp` — wasm arch macros (mirror ARM macros here).
- `compiler/ARM/arm-arch.lisp` — reference for ARM layout and arch macros.
- `level-0/WASM/wasm-def.lisp` — wasm‑only level‑0 overrides.
- `level-1/linux-files.lisp` — wasm‑only OS/FFI stubs used during fasl compile.
- `lib/systems.lisp` — wasm module wiring.
- `lib/compile-ccl.lisp` — wasm xload/compiler module lists.
- `scripts/wasm/compile-wasm-fasls.sh` — cross‑compile wasm fasls.
- `scripts/wasm/build-wasm-boot.{lisp,sh}` — build `wasm-boot.image`.
- `scripts/wasm/make-real-image.lisp` — real image policy; injects `:wasm32-target`.
- `doc/wasm/subprims-map.json` — subprims table map (stub entries).
- `scripts/wasm/generate_subprims_artifacts.py` — regenerates subprims map/headers.
- `lisp-kernel/wasm-subprims-provider.c` — stub entrypoints for macro‑apply/UDF.
- `doc/wasm/js/load-image.mjs` — host loader for boot/root images.
- `doc/wasm/js/make-real-image.mjs` — optional wasm‑only root image helper.
- `lisp-kernel/unix-calls.c` — wasm file I/O (read‑only today).

## Remaining Work Plan (Sequential)
1. Preflight (host + toolchain)
   - Confirm a 64‑bit host CCL is in use; `scripts/wasm/make-real-image.lisp`
     injects `:wasm32-target` into `*features*`.
   - Ensure Node is available for `doc/wasm/js/load-image.mjs`.
2. Build the wasm kernel and subprims provider.
   - Command: `make -C lisp-kernel/wasm32` and `make -C lisp-kernel/wasm32/subprims`.
   - Outputs: `doc/wasm/js/wasmcl.wasm` and `doc/wasm/js/subprims.wasm`.
3. Compile wasm fasls (level‑1 + l1‑fasls).
   - Command: `scripts/wasm/compile-wasm-fasls.sh`.
   - Outputs: `level-1.lafsl`, `l1-fasls/*.lafsl`, `bin/*.lafsl`.
   - If compilation fails:
     - Add missing arch macros to `compiler/WASM/wasm-arch.lisp`
       (mirror `compiler/ARM/arm-arch.lisp`).
     - Add missing opcode handlers or fallbacks in `compiler/WASM/wasm2.lisp`
       (for example, the `complex` fallback).
     - Keep wasm‑only OS/FFI stubs in `level-1/linux-files.lisp`.
4. Ensure xfasload stays in sync on the host (completed).
   - ARM package inclusion and wasm xload fixes are in place.
   - If `xdump/xfasload.lisp` changes, rebuild `xdump/xfasload.dx64fsl`:
     ```lisp
     ccl --no-init --batch -e '(require "FASLENV" "ccl:xdump;faslenv")
       (compile-file "ccl:xdump;xfasload.lisp"
                     :output-file "ccl:xdump;xfasload.dx64fsl")'
     ```
5. Produce the boot image (completed).
   - Command: `scripts/wasm/build-wasm-boot.sh --force`.
   - Output: repo root `wasm-boot.image` (logical `ccl:ccl;wasm-boot.image`).
6. Verify subprims stub indices are in sync.
   - Keep `xdump/xwasmfasload.lisp` constants aligned with
     `doc/wasm/subprims-map.json`; regenerate via
     `scripts/wasm/generate_subprims_artifacts.py` if the map changes.
7. Validate the boot image in the wasm runtime.
   - Command: `node doc/wasm/js/load-image.mjs --start-lisp BOOT_IMAGE_PATH`.
   - If it traps, fix the first missing stub/op and repeat.
8. Generate and validate the real root image (current host path).
   - Command: run `scripts/wasm/make-real-image.lisp` under host CCL.
   - Output: `doc/wasm/root.image`, then
     `node doc/wasm/js/load-image.mjs --start-lisp doc/wasm/root.image`.
9. Optional: implement wasm‑only `save-application` output.
   - Action: add write/lseek/ftruncate in `lisp-kernel/unix-calls.c` and a
     persistence extraction path, then use `doc/wasm/js/make-real-image.mjs`.

## Completion Criteria (Exit to Main‑Loop Work)
- `scripts/wasm/build-wasm-boot.sh` (or `(cross-xload-level-0 :wasm32)`)
  produces a wasm boot image with no errors.
- `doc/wasm/js/load-image.mjs --start-lisp BOOT_IMAGE_PATH` enters Lisp without
  immediate macro‑apply/UDF traps.
- `scripts/wasm/make-real-image.lisp` (injects `:wasm32-target` if missing)
  produces `doc/wasm/root.image`, and
  `node doc/wasm/js/load-image.mjs --start-lisp doc/wasm/root.image` works
  (wasm‑only save path optional).
- No non‑WASM behavior changes outside `#+wasm32-target` guards.
