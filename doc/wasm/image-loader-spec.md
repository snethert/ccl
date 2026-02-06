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
registry before entering `start_lisp` or stepping the toplevel.

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

## Reference host placement strategy (current)

The Node helper (`doc/wasm/js/load-image.mjs`) uses:

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
- What is the policy for “root image” caching and clone‑from‑image?
- How does dynamic module loading interact with images?
