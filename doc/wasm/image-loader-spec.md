# Image Loader Specification

**Status:** Active
**Scope:** Kernel ABI for loading CCL heap images in WASM runtime
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

## Purpose

This document defines the stable ABI between the WASM kernel and host JavaScript for loading CCL heap images into linear memory. It covers the boot-only path required for MVP-1 (Library Mode) and documents the post-load fixup sequence.

This specification focuses on bringing up a working image loader. Long-term image format design and dynamic module loading semantics are out of scope.

## Current Implementation Status

### ✅ What Works

- **Image byte loading:** `wasm_ccl_load_image()` successfully copies image data into linear memory
- **Section mapping:** Image sections (readonly, dynamic, static) map correctly
- **Memory layout:** Kernel respects host-provided cstack bounds and image placement
- **Symbol structure:** Symbol objects exist in loaded memory with correct internal structure
- **Boot-only mode:** Returns control to host after loading without entering toplevel
- **RESTORE-LISP-POINTERS:** Called after image load to rebuild package hash tables (fixed 2026-02-15)
- **Boot image auto-build:** `make-real-image.mjs` automatically triggers boot image build when missing

### ❌ Critical Issues (MVP-1 Blockers)

**Compiled module installation skips 99.97% of modules**

The image loader and RESTORE-LISP-POINTERS work correctly. The current blocker is downstream: the compiled module installer rejects 7555 of 7557 modules during root image build, leaving function table entries unpopulated. When FASL loading subsequently attempts to call compiled functions, it traps with "table index is out of bounds."

This is tracked as blocker B2 in [TODO.md](../../TODO.md).

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
| -3   | Function not defined (expected for boot images before level-1 is loaded) |
| -7   | Symbol lookup failure during boot |
| Other | Kernel-specific error codes |

## Host Requirements

Hosts must perform these steps before calling `wasm_ccl_load_image()`:

1. **Allocate linear memory:** Size must accommodate image + cstack + scratch space
2. **Configure cstack:** Call `wasm_set_cstack_bounds(base, size)` to define C stack region
3. **Place image bytes:** Copy image file into linear memory at 16-byte aligned address
4. **Ensure non-overlap:** Image, cstack, and scratch regions must not overlap

Memory layout is a host policy decision. The reference implementation ([`scripts/wasm/lib/make-real-image.mjs`](../../scripts/wasm/lib/make-real-image.mjs)) uses:
- Cstack at top of linear memory
- Image blob placed below cstack (16-byte aligned)
- Small scratch reserve below image

## Post-Load Fixup: RESTORE-LISP-POINTERS

After loading an image, `RESTORE-LISP-POINTERS` must be called to:
1. Rehash package hash tables (makes symbols findable via `FIND-SYMBOL`/`INTERN`)
2. Refresh FFI entrypoints
3. Run registered fixup hooks
4. Initialize interactive streams

This matches native CCL behavior where the toplevel function calls `restore-lisp-pointers` from [`lib/dumplisp.lisp:328`](../../lib/dumplisp.lisp#L328).

### Implementation

The kernel exports `wasm_restore_lisp_pointers()` as a standalone callable function:

```c
int32_t wasm_restore_lisp_pointers(void);
```

| Return Code | Meaning |
|-------------|---------|
| 0 | Success |
| -3 | Function not defined (boot image, level-1 not loaded yet) |
| Other | Error |

**Timing in `make-real-image.mjs`:**

1. **Early call** (after image load, before FASLs): Returns -3 for boot images because RESTORE-LISP-POINTERS is a level-1 function not yet defined. This is expected — boot image hash tables are freshly built and valid.
2. **Post-fasload call** (after level-1 FASLs loaded): Should succeed (rc=0), rehashing any tables built during FASL loading.

```
Boot image:  load_image → restore-lisp-pointers (rc=-3, deferred) → fasload → restore-lisp-pointers (rc=0)
Saved image: load_image → restore-lisp-pointers (rc=0) → toplevel
```

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
3. Writes boot image to `build/wasm32/wasm-boot.image`

### Auto-Build

When `make-real-image.mjs` finds the boot image missing at `build/wasm32/wasm-boot.image`, it automatically runs `scripts/wasm/build-wasm-boot.sh` to create it. This avoids a manual build step.

### Output Location

**Location:** `build/wasm32/wasm-boot.image`

Output path is specified in [`xdump/xwasmfasload.lisp:72`](../../xdump/xwasmfasload.lisp#L72):
```lisp
:default-image-name "ccl:build;wasm32;wasm-boot.image"
```

### Image Contents

The boot image contains:
- All level-0 runtime code (package system, basic I/O, error handling)
- Core symbols including `CCL::%FASLOAD`
- Static nilreg (nil-relative symbols) section
- Package hash tables (freshly built, valid without fixup)

## Testing & Validation

### Boot-Only Mode

Verify image loads without entering toplevel:

```bash
node scripts/wasm/lib/load-image.mjs --mode boot-only build/wasm32/wasm-boot.image
```

Expected: Returns 0, no errors.

### Start-Lisp Mode

Attempt to enter toplevel after loading:

```bash
node scripts/wasm/lib/load-image.mjs --mode start-lisp build/wasm32/wasm-boot.image
```

**Current result:** Image loads and RESTORE-LISP-POINTERS is deferred (rc=-3, expected for boot image). FASL loading fails due to compiled module installation issue (B2).

### Full Load Test (Blocked by B2)

Test loading with compiled modules:

```bash
node scripts/wasm/lib/make-real-image.mjs \
  --modules build/wasm32/modules/wasm-runtime-modules.json \
  --output build/wasm32/images/root.image
```

**Current result:** 7555/7557 compiled modules skipped, FASL loading traps with "table index is out of bounds."

## Implementation Notes

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
- [Roadmap](./roadmap.md) – MVP-1 vs MVP-2 strategy
- [Project Overview](./project-overview.md) – High-level architecture vision
- [Build](./build.md) – Build instructions and build pipeline
