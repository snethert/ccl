# Image Loader Specification (WASM)

**Status:** Draft  
**Scope:** Defines how a WASM runner receives a Lisp heap image and how the
kernel consumes it. This is a bring‑up spec; it does not define the long‑term
image format or module‑level loader semantics.

## Goals

- Allow a host to place an image in linear memory and ask the kernel to boot.
- Keep the ABI stable while real toplevel/loader integration is developed.
- Support a minimal “boot‑only” path for early verification.

## Non‑goals

- Define the image file format (assumed to be CCL‑compatible for now).
- Provide a full module loader or dynamic linker.
- Automatically enter the Lisp toplevel loop as part of image load.

## Current ABI

The kernel exports:

```
wasm_ccl_load_image(image_bytes_ptr: u32, image_bytes_len: u32) -> i32
wasm_ccl_start_lisp() -> i32
```

Host responsibilities:

1. Ensure `env.memory` is large enough for the image + cstack + scratch space.
2. Call `wasm_set_cstack_bounds(base, size)` before entering Lisp.
3. Copy image bytes into linear memory at a safe address.
4. Call `wasm_ccl_load_image(ptr, len)`.

Kernel behavior (current bring‑up):

- Stores the image pointer/length via `wasm_set_boot_image`.
- Sets `wasm_boot_only = 1`.
- Calls `wasm_ccl_start()`, which returns to the host after loading the image.

Optional host entry paths (current bring‑up):

- **Boot-only:** `wasm_ccl_load_image(ptr, len)` (returns to host).
- **Boot + start_lisp (post‑load):** `wasm_ccl_load_image(ptr, len)` then
  `wasm_ccl_start_lisp()`. The host must ensure the function table contains the
  entrypoint index used by the image (the minimal image uses table index 200 → `wasm_boot_entry`).
- **Boot + start_lisp (direct):** `wasm_set_boot_image(ptr, len)` then `wasm_ccl_start()`.
- **Explicit toplevel:** `wasm_run_toplevel()` (one-shot) or `wasm_ccl_step()` (host‑stepped).

If the image references compiled modules, the host should install them from the
registry before entering `start_lisp` or stepping the toplevel. The current
boot images do not always populate the registry; for bring‑up the host uses an
external compiled‑modules bundle (JSON + `.bin` sidecar) produced by
`scripts/wasm/compile-wasm-fasls.sh --modules-out …` and loads it via
`doc/wasm/js/load-image.mjs --modules ...`.

## Real Image Policy (Seed)

For “real” WASM images (as opposed to the minimal stub image), the image build
path must seed the kernel toplevel function explicitly:

- `%toplevel-function%` (NRS index 16) is set to `toplevel-loop` in the image.
  The kernel copies this into the VSP toplevel slot before entering
  `start_lisp`.
- `%wasm-compiled-modules%` (NRS index 33) may contain the compiled‑modules
  registry. If non‑NIL, the host should install these modules before entering
  `start_lisp`.

The seed image build script is `scripts/wasm/make-real-image.lisp`.
It will inject `:wasm32-target` into `*features*` if needed, so a normal
64‑bit host CCL (including a native macOS build) is sufficient for the
current workflow and there is no 32‑bit host requirement.
The Node‑hosted helper (`doc/wasm/js/make-real-image.mjs`) now supports
the wasm‑only save path by calling `wasm_save_image_direct` and extracting
the result from persistence storage.
On non-WASM hosts, the Lisp script preserves direct-host workflow by
delegating to the Node helper.
The boot image it consumes is produced via `cross-xload-level-0 :wasm32`
(wrapper: `scripts/wasm/build-wasm-boot.sh`), which now completes and writes
`ccl:ccl;wasm-boot.image`.

The JS loader and Node helper accept `--modules PATH` and will load the
compiled‑modules bundle before `start_lisp`. This is required for real images
until the compiled‑modules registry is reliably embedded in the image.

## Artifact Contract (Current)

Runtime compiled modules are consumed as a v2 bundle contract:

- manifest: `ccl-wasm-modules-v2` JSON (`.json`)
- binary sidecar (`.bin`)
- index sidecar (`.idx`)

`scripts/wasm/compile-wasm-fasls.sh --modules-out ...` now emits this contract
by compiling inline bundle data and repacking it through
`scripts/wasm/pack-inline-bundle-v2.mjs`.

Real image generation now writes a root-image manifest by default:

- image: `doc/wasm/root.image`
- manifest: `doc/wasm/root.image.manifest.json`
- schema: `doc/wasm/root-image-manifest.schema.json`

The manifest includes SHA-256 checksums for:

- root image
- runtime modules manifest/binary/index
- `wasmcl.wasm`
- `subprims.wasm`

The loader can validate this contract pre-boot via:

`doc/wasm/js/load-image.mjs --manifest ...`

## Loader Modes and Non-Interactive Controls

`doc/wasm/js/load-image.mjs` now supports explicit modes:

- `--mode boot-only`
- `--mode start-lisp`
- `--mode run-toplevel`

Compatibility aliases remain:

- `--start-lisp` -> `--mode start-lisp`
- `--run` -> `--mode run-toplevel`

Policy/validation controls:

- `--manifest PATH` (hash validation before boot)
- `--strict-modules` / `--allow-partial-modules`
- `--expect-rc N`

Non-interactive stdin preload:

- `--stdin-script PATH`
- `--stdin-text TEXT`
- `--close-stdin`

Current status:

- Minimal-image non-interactive `start_lisp` validation is green.
- Strict root-image non-interactive `start_lisp` validation still times out
  (tracked by `start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`).

## Reference host placement strategy (current)

The JS host loader (`doc/wasm/js/load-image.mjs`) uses:

- A manual cstack at the top of linear memory.
- The image blob placed just below the cstack (16‑byte aligned).
- A small scratch “reserve” area below the image.

This is a policy decision for bring‑up and **not** a requirement of the ABI.
Hosts may choose a different layout as long as it does not overlap with the
cstack or the image.

## Invariants

- The image bytes are treated as **read‑only input** by the kernel.
- The kernel does **not** retain host pointers; it only remembers offsets.
- The host must not move the image once `wasm_ccl_load_image` is invoked.

## Open Questions

- What is the canonical image format for WASM (raw CCL heap image vs. WASM‑native)?
- Do we need image versioning or metadata (endianness, word size, tag layout)?
- How does dynamic module loading interact with images?
