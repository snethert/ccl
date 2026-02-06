# WASM Image Proposal: Zero-Bias Base + Embedded Compiled Modules

## Goals
- Keep the existing OpenMCL image format and loader logic.
- Eliminate relocation on WASM by matching the image base to the runtime heap base.
- Embed an initial compiled-modules registry in the image so the host can install
  modules without shipping a separate registry payload.
- Preserve platform/ABI gating and compatibility checks.

## Context (What We Already Have)
- The OpenMCL image format uses a header/trailer scheme; the header can be
  anywhere and the trailer at EOF points back to it. This lets us embed images
  inside larger artifacts (bundle + append).
- The loader validates ABI and platform flags before mapping sections.
- On WASM, image sections are copied into linear memory (no mmap), and
  Protect/UnProtect are no-ops.
- The WASM bring-up already supports an image-resident compiled-modules registry
  at NRS index 33 (`%wasm-compiled-modules%`).

## Proposed Layout (WASM Zero-Bias Image)

### Format
We keep the standard OpenMCL image format and section set:
- static
- readonly
- dynamic
- managed static
- static cons

The only change is the value of `actual_image_base` in the header:
- `canonical_image_base` remains `IMAGE_BASE_ADDRESS` (0 for WASM32).
- `actual_image_base` is set to the runtime heap base used by the kernel.

### Zero-Bias Base
On WASM, the kernel reserves the heap at an address derived from `__heap_base`
(aligned to heap segment size). The runtime computes:

```
heap_base = align(__heap_base, log2_heap_segment_size)
image_base = heap_base
bias = image_base - actual_image_base
```

If `actual_image_base == heap_base`, then `bias == 0` and relocation becomes a
no-op.

### Compiled Modules Registry (Embedded)
Embed a list of compiled module entries directly in the image and store the
registry pointer in `nrs_WASM_COMPILED_MODULES` (NRS index 33). Each entry is a
simple vector of:

- module bytes (u8 vector)
- export name (base string)
- entry index (fixnum)
- module version (fixnum)

This matches the existing bring-up registry shape and lets the host call
`installCompiledModulesFromRegistry` immediately after load.

### Optional Placement Optimization
Because WASM has no mprotect and MapFile already copies bytes, large compiled
module blobs can be placed in the readonly section to reduce GC pressure. The
registry list can remain in dynamic (or readonly) as long as the pointers are
valid and GC-visible.

## Host Contract (Loader Path)

1. Instantiate `wasmcl.wasm`.
2. Read the runtime heap base (`wasm_get_heap_base` export; see below).
3. Verify the image header’s `actual_image_base` matches the heap base.
   - If mismatch: either reject or accept relocation (fallback path).
4. Place image bytes into linear memory and call `wasm_ccl_load_image`.
5. Install compiled modules from the embedded registry.
6. Install the boot entrypoint (`wasm_boot_entry` at table index 200).
7. Enter `start_lisp` or `wasm_run_toplevel`.

## Required Changes

### Kernel (WASM)
Add a small helper to expose the runtime heap base to the host. This avoids
hardcoding toolchain-specific values.

- New export:
  - `wasm_get_heap_base() -> u32`
- Implementation uses the same alignment logic as `ReserveMemoryForHeap`.

### Image Generator
Update `scripts/wasm/make_minimal_image.py` (and the real image build path) to
accept an explicit `actual_image_base`.

- New argument:
  - `--actual-base <hex>`
- Optional auto mode:
  - `--kernel <path/to/wasmcl.wasm>`
  - a small helper instantiates the wasm module and reads
    `wasm_get_heap_base` to supply `--actual-base`.

The generator should continue to set the compiled-modules registry pointer in
NRS index 33, and embed module bytes in dynamic or readonly sections.

### JS Loader (doc/wasm/js)
- Use `wasm_get_heap_base` to validate zero-bias images.
- If the image base mismatches, log a warning and continue with relocation, or
  reject (policy choice).

## Benefits
- Zero relocation in the common case (faster startup, simpler debugging).
- Clear, toolchain-verified contract for image compatibility.
- Embedded compiled modules reduce JS-side packaging and runtime work.
- Works with the existing OpenMCL image format and loader.

## Risks / Open Questions
- `__heap_base` can shift if the kernel is rebuilt with different toolchain
  flags or link order. Exporting a helper avoids hardcoding.
- Readonly section sizing (`PURESPACE_SIZE` for ARM/WASM is 32 MiB) may limit
  how much compiled module data can live in readonly.
- If we choose to allow relocation fallback, we should define a clear policy
  for when a mismatch is a hard error vs a warning.

## Next Steps
1. Add `wasm_get_heap_base` export and wire it into `wasm32/Makefile`.
2. Extend `make_minimal_image.py` to accept `--actual-base`.
3. Add a tiny helper script to read the heap base from `wasmcl.wasm`.
4. Update the JS loader to verify base and log mismatch.
5. Document the zero-bias contract in `doc/wasm/image-loader-spec.md`.
