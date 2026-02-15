# Image Loader Specification

**Status:** Active – Blocking issues prevent FASL loading
**Scope:** Kernel ABI for loading CCL heap images in WASM runtime
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

## Purpose

This document defines the stable ABI between the WASM kernel and host JavaScript for loading CCL heap images into linear memory. It covers the boot-only path required for MVP-1 (Library Mode) and documents the critical missing fixup step that currently prevents FASL loading.

This specification focuses on bringing up a working image loader. Long-term image format design and dynamic module loading semantics are out of scope.

## Current Implementation Status

### ✅ What Works

- **Image byte loading:** `wasm_ccl_load_image()` successfully copies image data into linear memory
- **Section mapping:** Image sections (readonly, dynamic, static) map correctly
- **Memory layout:** Kernel respects host-provided cstack bounds and image placement
- **Symbol structure:** Symbol objects exist in loaded memory with correct internal structure
- **Boot-only mode:** Returns control to host after loading without entering toplevel

### ❌ Critical Issues (MVP-1 Blockers)

**FASL loading fails with error code -7**

Root cause: Package hash tables are never rebuilt after image load.

Native CCL always calls `RESTORE-LISP-POINTERS` after loading an image to:
1. Rehash package hash tables (makes symbols findable)
2. Refresh FFI entrypoints
3. Run registered fixup hooks
4. Initialize interactive streams

WASM never calls this function. Image load sequence comparison:

```
Native CCL:  load_image → map sections → restore-lisp-pointers → toplevel
WASM:        load_image → map sections → [MISSING] → toplevel
```

Impact:
- Symbols exist but cannot be found via `wasm_find_symbol_named_bytes()`
- `INTERN` operations fail
- Cannot load `level-1.lafsl` (needs to find `CCL::%FASLOAD`)
- Dynamic loading impossible

**Required fix:** Call `RESTORE-LISP-POINTERS` in [`lisp-kernel/wasm-kernel-stubs.c`](../../lisp-kernel/wasm-kernel-stubs.c) before entering toplevel.

See [§ Implementation Notes](#implementation-notes) for proposed C code.

## Kernel ABI

The kernel exports two entry points for image loading:

```c
// Load image bytes into linear memory, return to host
int32_t wasm_ccl_load_image(uint32_t image_ptr, uint32_t image_len);

// Enter Lisp toplevel (call after wasm_ccl_load_image)
int32_t wasm_ccl_start_lisp(void);
```

### Return Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| -7   | Symbol lookup failure during boot (current blocker) |
| Other | Kernel-specific error codes |

## Host Requirements

Hosts must perform these steps before calling `wasm_ccl_load_image()`:

1. **Allocate linear memory:** Size must accommodate image + cstack + scratch space
2. **Configure cstack:** Call `wasm_set_cstack_bounds(base, size)` to define C stack region
3. **Place image bytes:** Copy image file into linear memory at 16-byte aligned address
4. **Ensure non-overlap:** Image, cstack, and scratch regions must not overlap

Memory layout is a host policy decision. The reference implementation ([`scripts/wasm/lib/load-image.mjs`](../../scripts/wasm/lib/load-image.mjs)) uses:
- Cstack at top of linear memory
- Image blob placed below cstack (16-byte aligned)
- Small scratch reserve below image

## Boot Image Build Process

The WASM boot image is created via cross-compilation from a native CCL host.

### Build Script

[`scripts/wasm/build-wasm-boot.sh`](../../scripts/wasm/build-wasm-boot.sh)

Invokes:
```bash
ccl --no-init --batch -l scripts/wasm/build-wasm-boot.lisp [-- --force]
```

This calls `cross-xload-level-0 :wasm32` which:
1. Loads WASM backend compiler
2. Cross-compiles all level-0 Lisp runtime FASLs
3. Writes boot image to `ccl:ccl;wasm-boot.image`

### Output Location

**Current:** `wasm-boot.image` at repository root
**Future:** Should relocate to `build/wasm32/` for proper build hygiene

Output path is specified in [`xdump/xwasmfasload.lisp:72`](../../xdump/xwasmfasload.lisp#L72):
```lisp
:default-image-name "ccl:ccl;wasm-boot.image"
```

### Image Contents

The boot image contains:
- All level-0 runtime code (package system, basic I/O, error handling)
- Core symbols including `CCL::%FASLOAD`
- Static nilreg (nil-relative symbols) section
- Package hash tables (in stale state until fixup runs)

## Testing & Validation

### Boot-Only Mode

Verify image loads without entering toplevel:

```bash
node scripts/wasm/lib/load-image.mjs --mode boot-only wasm-boot.image
```

Expected: Returns 0, no errors.

### Start-Lisp Mode (Currently Broken)

Attempt to enter toplevel after loading:

```bash
node scripts/wasm/lib/load-image.mjs --mode start-lisp wasm-boot.image
```

**Current result:** May succeed for minimal images, fails when attempting FASL load (error -7).

### Full Load Test (Blocked)

Test loading level-1 FASL bundle:

```bash
node scripts/wasm/lib/load-image.mjs \
  --mode start-lisp \
  --modules path/to/compiled-modules-v2.json \
  wasm-boot.image
```

**Current result:** Fails with -7 when trying to intern `CCL::%FASLOAD`.

## Implementation Notes

### Proposed Fix: Call RESTORE-LISP-POINTERS

In [`lisp-kernel/wasm-kernel-stubs.c`](../../lisp-kernel/wasm-kernel-stubs.c) function `start_lisp()`, before calling `wasm_toplevel_loop()`:

```c
// Rebuild package hash tables and run fixup hooks
LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.vcell;
if (restore_fn != lisp_nil &&
    fulltag_of(restore_fn) == fulltag_misc &&
    header_subtag(header_of(restore_fn)) == subtag_function) {

    tcr->wasm_gprs[nargs] = box_fixnum(0);
    tcr->wasm_gprs[nfn] = restore_fn;
    wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX));

    if (tcr->wasm_pending_throw) {
        // Fixup failed, abort boot
        goto done;
    }
}
```

This matches native CCL behavior where the toplevel function calls `restore-lisp-pointers` from [`lib/dumplisp.lisp:328`](../../lib/dumplisp.lisp#L328).

### ABI Invariants

- **Read-only input:** Image bytes are not modified by the kernel
- **No retained pointers:** Kernel stores offsets, not host-side pointers
- **Immutable after load:** Host must not move image data after calling `wasm_ccl_load_image()`

## Future Work

Deferred to MVP-2 or later:

- ⏸️ Image format versioning and metadata (endianness, word size, tag layout)
- ⏸️ WASM-native image format (vs. current CCL-compatible format)
- ⏸️ Embedded compiled-modules registry in image (currently external JSON bundle)
- ⏸️ Dynamic module loading integration

## Related Documentation

- [Porting Status](./porting-status.md) – Overall feature implementation status
- [Bootstrap Architecture](./bootstrap-wasm32.md) – Level-0/Level-1 bootstrap sequence
- [Roadmap](./roadmap.md) – MVP-1 vs MVP-2 strategy
- [Project Overview](./project-overview.md) – High-level architecture vision
