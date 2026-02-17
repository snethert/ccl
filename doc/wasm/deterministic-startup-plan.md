# Deterministic Startup: Complete Build Pipeline Plan

## Design Principles

1. **Build-time completeness**: Every decision, resolution, and installation happens at build. Launch makes zero decisions.
2. **The image is the truth**: After build, root.image contains ALL Lisp state — heap objects, installed const pools, resolved symbols, interned packages. Nothing computed at launch that was already computed at build.
3. **Launch = restore + reconnect**: Load the heap snapshot. Reinstantiate WASM modules. Fill the function table. Start. Three operations — no parsing, no scanning, no resolving, no const pool installation.
4. **Everything is modifiable**: Image base address, module format, microkernel, file layouts, build pipeline — all redesigned for launch speed.
5. **Delete, don't adapt**: Dead code gets removed entirely. `bootstrap-contract.mjs` (163 lines), `bootstrap-function-resolver.mjs` (975 lines) — deleted, not refactored.
6. **Zero relocation by construction**: Image base address = `__heap_base`. Bias = 0. No pointer rewriting at launch.
7. **Parallel where possible**: WASM module compilation at launch uses `Promise.all()`. Sequential only where dependencies demand it.

---

## Context

The WASM port's root.image build is blocked at B6. Two root causes:
1. **280+ ARM LAP bridge functions have no WASM equivalents.** Cold-boot init throws at step 30 (`%store-node-conditional` XNOFUN). FASL loading fails with `%GET-ERRNO` XNOFUN.
2. **The runtime launcher performs dynamic work at launch** (scanning, parsing, symbol resolution, on-demand const pool installation) that belongs at build time.

**User directives:**
- "We shouldn't be mapping a darn thing at load time. Just looping over known quantities."
- "YES YOU DO" need all 280+ functions. No cutting corners.
- "You are allowed to change literally *anything* which will make startup easy and fast: code, file formats, the image...whatever."

### Already Implemented (Phase 1a-1c)
- `%run-cold-boot-init` extracted → [nfasload.lisp:1243-1286](level-0/nfasload.lisp#L1243-L1286)
- `wasm_run_cold_boot_init()` C export → [wasm-kernel-stubs.c:3109-3175](lisp-kernel/wasm-kernel-stubs.c#L3109-L3175)
- JS-side call → [make-real-image.mjs:1207-1214](scripts/wasm/lib/make-real-image.mjs#L1207-L1214)

### Blocked At
- Cold-boot init throws: `record-system-lock` → `atomic-push-uvector-cell` → `%store-node-conditional` (XNOFUN)
- FASL loading: `%GET-ERRNO` (XNOFUN) in error handler chain

### B6 Failure Chain
```
l1-cl-package.lafsl → %STRING-TO-STDERR → %NEW-GCABLE-PTR → MAKE-GCABLE-MACPTR
  → lisp_write(fd=16899495) → fail → error handler → %GET-ERRNO → XNOFUN
  → funcall-error → ksignalerr → pending_throw → fasload returns -72
```

---

## Key Architectural Insight: Image State vs Host State

When `make-real-image.mjs` saves root.image, it snapshots five heap areas (`nilreg`, `readonly`, `dynamic`, `managed-static`, `static-cons`) via direct `writebuf(fd, area->low, memory_size)` in [image.c:778-801](lisp-kernel/image.c#L778-L801).

**IN the saved image (serializable Lisp state):**
- All Lisp objects (symbols, strings, conses, vectors, closures, etc.)
- Function vectors with entry indices (fixnums baked into heap)
- Package hash tables, class hierarchy, CLOS metadata
- Any const pool data that was installed into the heap during build

**NOT in the saved image (host objects, not serializable):**
- WASM function references (`WebAssembly.Function` objects in `WebAssembly.Table`)
- Compiled WASM module instances (V8 native code)
- The JS-side const pool byte cache

**Current problem:** Const pools are installed ON-DEMAND via `wasm_host_install_const_pool()` callbacks (`installConstPools: false` on [make-real-image.mjs line 1118](scripts/wasm/lib/make-real-image.mjs#L1118)). Only const pools for functions that were actually CALLED during build get installed. Unexecuted functions have uninstalled pools. At launch, the on-demand mechanism fires for those, requiring the launcher to carry const pool data and installation logic.

**Solution (Phase 2A):** Proactively install ALL const pools at build time, after FASL loading completes but before saving. The saved image then contains ALL installed const pool data. At launch: ZERO const pool work.

**Therefore, launch reduces to:**
1. Load image into memory (zero relocation — bias = 0)
2. Reinstantiate WASM modules (parallel `WebAssembly.compile()`)
3. Fill function table (entry index → WASM function)
4. Call `wasm_ccl_start_lisp()`

---

## Kernel-JS Communication: Request/Response Buffer ABI

The kernel communicates with the JS host via a **request/response buffer protocol** (NOT direct WASM function imports). Defined in [wasm-host.c](lisp-kernel/wasm-host.c):

```
kernel_request(opcode, payload_ptr, payload_len) → request_id
kernel_poll(request_id) → status (PENDING=0, DONE=1, ERROR=2)
kernel_result(request_id) → int32 result
kernel_copy_response(request_id, out_buf, out_cap) → bytes_copied
kernel_drop_request(request_id) → void
```

These are WASM imports that the kernel module expects. **The import contract must be preserved** — changing it requires rebuilding the kernel. The microkernel rewrite (Phase 3) simplifies the JS *implementation* behind these imports, not the import signatures.

**Request opcodes** (from [microkernel.mjs](scripts/wasm/lib/microkernel.mjs)):

| Category | Opcodes | Status |
|----------|---------|--------|
| Stream I/O | WRITE, READ, OPEN, CLOSE, SEEK, TRUNCATE | Essential — keep |
| File System | PROBE, TRUENAME, DIRECTORY, FILE_WRITE_DATE, RENAME, DELETE, ENSURE_DIRS | Keep (stub for MVP-1) |
| UI | POLL, RENDER, MEASURE_TEXT | MVP-2 — stub |
| Runtime | EVENT, COMMAND_POLL, COMPILED_MODULES_REFRESH | Keep for dynamic compilation |
| System | CAPS, LOG, TIME_NOW | Essential — keep |

---

## Build Pipeline (5 Stages)

| # | Script | Outputs | Key Change |
|---|--------|---------|-----------|
| 1 | `make -C lisp-kernel/wasm32` | `wasmcl.wasm` | **Extract `__heap_base`** → sidecar file |
| 2 | `make -C lisp-kernel/wasm32/subprims` | `subprims.wasm` | (unchanged) |
| 3 | `build-wasm-boot.sh` → `cross-xload-level-0 :wasm32` | `wasm-boot.image`, modules, `.next-entry-index` | **Use extracted `__heap_base` as image base** |
| 4 | `compile-wasm-fasls.sh --start-entry-index N` | Runtime modules (V2 bundle) | (unchanged) |
| 5 | `make-real-image.mjs` | `root.image`, **`startup-plan.json`**, **`modules.bin`** | **Proactive const pool install**, **emit launch artifacts** |

**Cross-loader autodiscovery** ([xwasmfasload.lisp:74](xdump/xwasmfasload.lisp#L74)): `:subdirs '("ccl:level-0;WASM;")`. New `.lisp` files in `level-0/WASM/` auto-compiled and included in boot image. Subdirs load FIRST (alphabetically), before root `level-0/` files.

**Critical handoff:** Stage 3 writes `*wasm2-next-entry-index*` to sidecar → Stage 4 reads it. ~830 boot + ~7557 runtime = ~8387 total entries.

---

## Phase 0: Complete WASM Foundation

Two sub-phases with no dependencies. Can be implemented in parallel.

### Phase 0A: All 280+ LAP Bridge Functions

**Goal:** Define WASM equivalents for EVERY function currently defined as ARM LAP in `level-0/ARM/`. No incremental discovery. No guessing. All 280+ functions, up front.

**Approach:** Pure Lisp definitions in new files under `level-0/WASM/`. WASM is single-threaded, so all atomic operations become simple read-modify-write. Files are automatically included in the boot image via cross-loader autodiscovery.

#### Cross-reference: ARM Source Files → WASM Target Files

| ARM Source | Functions | WASM Target File |
|-----------|-----------|-----------------|
| `arm-misc.lisp` | 60 | `wasm-misc.lisp` (NEW) |
| `arm-def.lisp` | 35 | `wasm-def.lisp` (extend existing) |
| `arm-utils.lisp` | 45 | `wasm-utils.lisp` (NEW) |
| `arm-bignum.lisp` | 75 | `wasm-bignum.lisp` (NEW) |
| `arm-float.lisp` | 35 | `wasm-float.lisp` (NEW) |
| `arm-array.lisp` | 25 | `wasm-array.lisp` (NEW) |
| `arm-hash.lisp` | 15 | `wasm-hash.lisp` (NEW) |
| `arm-numbers.lisp` | 20 | `wasm-numbers.lisp` (NEW) |
| `arm-clos.lisp` | 10 | `wasm-clos.lisp` (NEW) |
| `arm-symbol.lisp` | 10 | `wasm-symbol.lisp` (NEW) |
| `arm-pred.lisp` | 2 | `wasm-pred.lisp` (NEW) |
| `arm-io.lisp` | 1 | `wasm-io.lisp` (NEW) |

#### Implementation Strategy by Category

##### Category A: Single-Threaded Atomics (trivial on WASM)
ARM uses `ldrex`/`strex` (CAS loops). WASM single-threaded = simple read-modify-write.

Functions: `%store-node-conditional`, `%store-immediate-conditional`, `%atomic-incf-node`, `%atomic-incf-ptr`, `%atomic-incf-ptr-by`, `%atomic-decf-ptr`, `%atomic-decf-ptr-if-positive`, `%atomic-swap-ptr`, `%ptr-store-conditional`, `%ptr-store-fixnum-conditional`, `%set-hash-table-vector-key-conditional`, `%atomic-pop-static-cons`, `xchgl`

Implementation pattern:
```lisp
(defun %store-node-conditional (offset object old new)
  (let ((actual (%fixnum-ref object offset)))
    (when (eq actual old) (%fixnum-set object offset new) t)))
```

##### Category B: Threading / Process Control (no-ops on single-threaded WASM)

Functions: `%lock-gc-lock`, `%unlock-gc-lock`, `%suspend-tcr`, `%resume-tcr`, `%suspend-other-threads`, `%resume-other-threads`, `%kill-tcr`, `%%tcr-interrupt`, `pending-user-interrupt`, `%check-deferred-gc`

Implementation: All return `nil`.

##### Category C: TCR / Kernel Global Access
ARM reads/writes TCR struct fields via register offsets. WASM needs either compiler intrinsics or C kernel exports.

Functions: `%current-tcr`, `%tcr-toplevel-function`, `%set-tcr-toplevel-function`, `interrupt-level`, `set-interrupt-level`, `%current-db-link`, `%no-thread-local-binding-marker`, `%get-os-context`, `%get-kernel-global-from-offset`, `%set-kernel-global-from-offset`, `%get-kernel-global-ptr-from-offset`, `%save-standard-binding-list`, `%saved-bindings-address`, `%catch-top`

**Must verify during implementation:** Which of these does the WASM compiler backend ([wasm2.lisp](compiler/WASM/wasm2.lisp)) already handle as intrinsics? For any it doesn't, add C kernel exports.

##### Category D: Memory / Pointer Operations
ARM reads/writes raw memory at fixnum-addressed offsets.

Functions: `%fixnum-ref`, `%fixnum-ref-natural`, `%fixnum-set`, `%fixnum-set-natural`, `%fixnum-address-of`, `%dnode-address-of`, `%uvector-data-fixnum`, `%misc-address-fixnum`, `fudge-heap-pointer`, `%%make-disposable`, `%vect-data-to-macptr`, `%ivector-from-macptr`, `%safe-get-ptr`, `%fixnum-from-macptr`, `%setf-macptr-to-object`, `%macptr->dead-macptr`, `%get-object`, `%set-object`, `%get-unboxed-ptr`, `%revive-macptr`, `%macptr-type`, `%macptr-domain`, `%set-macptr-type`, `%set-macptr-domain`

**Critical:** `%fixnum-ref` and `%fixnum-set` are FUNDAMENTAL — they translate to WASM `i32.load`/`i32.store`. The compiler MUST handle these as intrinsics. Verify in [wasm2.lisp](compiler/WASM/wasm2.lisp). If not intrinsic, need C exports: `wasm_fixnum_ref(fixnum, offset)`.

##### Category E: Bignum Arithmetic (75 functions)
Low-level 32-bit digit manipulation for arbitrary-precision integers.

Functions: `%bignum-ref`, `%ref-digit`, `%set-digit`, `%bignum-sign`, `%bignum-sign-bits`, `%digit-0-or-plusp`, `%bignum-oddp`, `bignum-plusp`, `%fixnum-to-bignum-set`, `bignum-minusp`, `%add-with-carry`, `%add-the-carry`, `%subtract-with-borrow`, `%multiply-and-add-harder-loop-2`, `%multiply-and-add`, `%multiply-and-add-fixnum-loop`, `%bignum-ref-hi`, `%bignum-set`, `%subtract-with-borrow-1`, `%subtract-one`, `%multiply-and-add-1`, `%logcount-complement`, `%logcount`, `bignum-add-loop-2`, `bignum-add-loop-+`, `bignum-negate-loop-really`, `bignum-negate-to-pointer`, `bignum-shift-right-loop-1`, `%compare-digits`, `%digits-sign-bits`, `bignum-logtest-loop`, `%bignum-lognot`, `%bignum-logand`, `%bignum-logandc2`, `%bignum-logandc1`, `digit-lognot-move`, `fix-digit-logandc2`, `fix-digit-logand`, `fix-digit-logandc1`, `%bignum-logior`, `%bignum-logxor`, `bignum-xor-loop`, `try-guess-loop-1`, `truncate-guess-loop`, `normalize-bignum-loop`, `%normalize-bignum-2`, `%count-digit-leading-zeros`, `%count-digit-trailing-zeros`, `%bignum-count-trailing-zero-bits`, `%bignum-trim-leading-zeros`, `%shrink-bignum`, `%floor-loop-quo`, `%floor-loop-no-quo`, `bignum-shift-left-loop`, `%floor-99`, `copy-limb`, `limb-zerop`, `compare-limbs`, `add-fixnum-to-limb`, `copy-fixnum-to-limb`, `mpn-incr-u`, `mpn-sub-n`, `mpn-add-n`, `mpn-add-1`, `mpn-mul-1`, `mpn-addmul-1`, `mpn-mul-basecase`, `mpn-lshift-1`, `umulppm`

**Implementation:** Pure Lisp using `uvref`/`(setf uvref)` to access bignum digit vectors. 32-bit digits. WASM native `i32` arithmetic maps well. Performance acceptable for bootstrap; optimize later with C helpers if needed.

```lisp
(defun %bignum-ref (bignum i) (uvref bignum i))
(defun %set-digit (bignum i digit) (setf (uvref bignum i) digit))
(defun %bignum-sign (bignum)
  (let ((hi (uvref bignum (1- (uvsize bignum)))))
    (if (logbitp 31 hi) -1 0)))
```

##### Category F: Float Operations (35 functions)
IEEE754 bit manipulation. ARM uses VFP instructions.

Functions: `%make-float-from-fixnums`, `%make-short-float-from-fixnums`, `%%double-float-abs!`, `%%short-float-abs!`, `%double-float-negate!`, `%short-float-negate!`, `%integer-decode-double-float`, `make-big-53`, `dfloat-significand-zeros`, `sfloat-significand-zeros`, `%%scale-dfloat!`, `%%scale-sfloat!`, `%copy-double-float`, `%copy-short-float`, `%double-float-exp`, `set-%double-float-exp`, `%short-float-exp`, `set-%short-float-exp`, `%short-float->double-float`, `%double-float->short-float`, `%int-to-sfloat!`, `%int-to-dfloat`, `%ffi-exception-status`, `%get-fpscr-control`, `%get-fpscr-status`, `%set-fpscr-status`, `%set-fpscr-control`, `%get-fpscr`, `%double-float-from-macptr!`, `%single-float-ptr->double-float-ptr`, `%double-float-ptr->single-float-ptr`, `%set-ieee-single-float-from-double`, `%double-float-sign`, `%short-float-sign`, `%single-float-sqrt!`, `%double-float-sqrt!`

**Implementation:** Pure Lisp using `uvref`/`(setf uvref)` for float object slots. Double-float = misc object with 2 words (hi/lo IEEE754 bits). Short-float = 32-bit IEEE754 inline. FPSCR functions (`%get-fpscr-control`, etc.): return 0 / ignore (no FP status register on WASM).

##### Category G: Array / Boole Operations (25 functions)

Functions: `%init-misc`, `%array-header-data-and-offset`, `%boole-clr`, `%boole-set`, `%boole-1`, `%boole-2`, `%boole-c1`, `%boole-c2`, `%boole-and`, `%boole-ior`, `%boole-xor`, `%boole-eqv`, `%boole-nand`, `%boole-nor`, `%boole-andc1`, `%boole-andc2`, `%boole-orc1`, `%boole-orc2`, `%aref2`, `%aref3`, `%aset2`, `%aset3`

**Implementation:** Pure Lisp. Boole operations iterate over bit vectors word-by-word applying the boolean operation.

##### Category H: Hash Table Operations (15 functions)

Functions: `fast-mod`, `fast-mod-3`, `%dfloat-hash`, `%sfloat-hash`, `%macptr-hash`, `%bignum-hash`, `%get-fwdnum`, `%get-gc-count`, `%set-hash-table-vector-key`, `%set-hash-table-vector-key-conditional`, `strip-tag-to-fixnum`

**Implementation:** Pure Lisp. `fast-mod` = `(mod number divisor)`. Hash functions extract bits from object representations.

**CRITICAL:** Hash values MUST match the native CCL hash functions exactly, or symbol lookup silently fails after image save/load. Verify against ARM LAP or kernel C implementation.

##### Category I: Number Operations (20 functions)

Functions: `%fixnum-signum`, `%ilogcount`, `%iash`, `%sfloat-hwords`, `%fixnum-intlen`, `%truncate-double-float->fixnum`, `%truncate-short-float->fixnum`, `%round-nearest-double-float->fixnum`, `%round-nearest-short-float->fixnum`, `%fixnum-truncate`, `called-for-mv-p`, `%fixnum-gcd`, `%mrg31k3p`, `%make-complex-double-float`, `%make-complex-single-float`

**Implementation:** Pure Lisp.

##### Category J: Symbol Operations (10 functions)

Functions: `%function`, `%symbol->symptr`, `%symptr->symbol`, `%symptr-value`, `%set-symptr-value`, `%symptr-binding-address`, `%tcr-binding-location`, `%pname-hash`, `%string-hash`, `%ensure-tlb-index`

**CRITICAL:** `%pname-hash` and `%string-hash` MUST produce identical values to the ARM implementation. The hash algorithm is a rotating XOR-add. Must match exactly or hash table lookups break silently. Verify by comparing output against native CCL (`dx86cl64`) for test strings.

##### Category K: Utils / GC / Heap (45 functions)

Functions: `%address-of`, `%normalize-areas`, `%active-dynamic-area`, `%object-in-stack-area-p`, `%object-in-heap-area-p`, `walk-static-area`, `%walk-dynamic-area`, `%class-of-instance`, `class-of`, `full-gccount`, `gc`, `%allocate-list`, `egc`, `%configure-egc`, `purify`, `impurify`, `lisp-heap-gc-threshold`, `set-lisp-heap-gc-threshold`, `use-lisp-heap-gc-threshold`, `allow-heap-allocation`, `heap-allocation-allowed-p`, `%ensure-static-conses`, `set-gc-notification-threshold`, `get-gc-notification-threshold`, `%kernel-import-internal`, `%get-unboxed-ptr`, `%revive-macptr`, `%macptr-type`, `%macptr-domain`, `%set-macptr-type`, `%set-macptr-domain`, `true`, `false`, `constant-ref`

**GC functions** (`gc`, `egc`, `purify`, `impurify`, `%configure-egc`): On WASM, GC is kernel C code. Call kernel exports if they exist; stub as no-ops if not.

**Area walking** (`walk-static-area`, `%walk-dynamic-area`): Iterate heap objects. Verify whether `%map-areas` (already in [l0-utils.lisp](level-0/l0-utils.lisp)) covers this.

##### Category L: CLOS (10 functions)

Functions: `%small-map-slot-id-lookup`, `%large-map-slot-id-lookup`, `%small-slot-id-value`, `%large-slot-id-value`, `%small-set-slot-id-value`, `%large-set-slot-id-value`, `funcallable-trampoline`, `unset-fin-trampoline`, `gag-one-arg`, `gag-two-arg`

**Implementation:** Pure Lisp. Slot ID lookup = linear/binary scan of class wrapper vectors.

##### Category M: Predicates (2 functions)

Functions: `eql`, `equal`

CL already defines these. ARM LAP provides fast paths. On WASM, compiler-generated versions should work. Define Lisp fallbacks as safety net.

##### Category N: Def / Frame Walking (35 functions)

Functions: `%current-frame-ptr`, `%current-vsp`, `%set-current-vsp`, `%%frame-backlink`, `%%frame-savefn`, `%cfp-lfun`, `%%frame-savevsp`, `%code-vector-pc`, `%do-ff-call`, `%apply-lexpr-with-method-context`, `%apply-with-method-context`, `%apply-lexpr-tail-wise`, `apply+`, `%lookup-subprim-address`, `arm-hard-float-p`, `%%apply-in-frame`, `%%save-application`

**Frame walking** (`%%frame-backlink`, `%%frame-savefn`, etc.): WASM has a different stack model (spill stack, not hardware frames). Need WASM-specific implementations based on spill stack layout.

**FF-call** (`%do-ff-call`): Foreign function calls via microkernel import mechanism. WASM-specific.

**`%%save-application`**: Delegates to `wasm_save_image_direct()` kernel export.

##### Category O: I/O (1 function)

Function: `%get-errno`

**Implementation:** Read the last WASI errno from a kernel global. The microkernel sets errno via its response codes. If `tcr->errno_loc` is maintained, read it. Otherwise return 0.

##### Category P: Ivector Copy Operations (8 functions)

Functions: `%copy-ptr-to-ivector-8bit`, `%copy-ptr-to-ivector-32bit`, `%copy-ivector-to-ptr-8bit`, `%copy-ivector-to-ptr-32bit`, `%copy-ivector-to-ivector-postincrement-8bit`, `%copy-ivector-to-ivector-postincrement-32bit`, `%copy-ivector-to-ivector-predecrement-8bit`, `%copy-ivector-to-ivector-predecrement-32bit`

**Implementation:** Byte/word copy loops using `uvref`/`(setf uvref)`.

#### Files to CREATE

| File | Functions | Lines (est.) |
|------|-----------|-------------|
| `level-0/WASM/wasm-misc.lisp` | 60 (atomics, threading, interrupt, memory, copy) | ~400 |
| `level-0/WASM/wasm-io.lisp` | 1 (%get-errno) | ~10 |
| `level-0/WASM/wasm-utils.lisp` | 45 (GC, heap, area walking, macptr) | ~300 |
| `level-0/WASM/wasm-bignum.lisp` | 75 (digit arithmetic) | ~600 |
| `level-0/WASM/wasm-float.lisp` | 35 (IEEE754 manipulation) | ~250 |
| `level-0/WASM/wasm-array.lisp` | 25 (boole ops, array access) | ~200 |
| `level-0/WASM/wasm-hash.lisp` | 15 (hash functions) | ~100 |
| `level-0/WASM/wasm-numbers.lisp` | 20 (fixnum/float operations) | ~150 |
| `level-0/WASM/wasm-clos.lisp` | 10 (slot lookup, trampolines) | ~100 |
| `level-0/WASM/wasm-symbol.lisp` | 10 (symbol ops, hashing) | ~80 |
| `level-0/WASM/wasm-pred.lisp` | 2 (eql, equal) | ~20 |
| **Total** | **~298** | **~2210** |

Plus extend existing [wasm-def.lisp](level-0/WASM/wasm-def.lisp) with ~35 frame/def operations (~250 lines).

#### Verification Strategy for Phase 0A

**Before implementation:** Read each ARM LAP function, understand its semantics, write the Lisp equivalent.

**Hash correctness:** Compare `%pname-hash`/`%string-hash` output for test strings between native CCL (`dx86cl64`) and the WASM Lisp implementation.

**Compiler intrinsics:** For `%fixnum-ref`, `%fixnum-set`, `%current-tcr`, `%set-tcr-toplevel-function`: check [wasm2.lisp](compiler/WASM/wasm2.lisp) to see if the WASM backend handles them as special forms. If yes, the Lisp definition is a fallback. If no, the definition IS the implementation (or C exports are needed).

### Phase 0B: Zero-Relocation Image Base

**Goal:** Set `:image-base-address` = `__heap_base` (aligned to 16 bytes) so the image loads at its natural address. Bias = 0. No relocation walk.

**How relocation currently works** ([image.c:66-145](lisp-kernel/image.c#L66-L145)):
- Computes `bias = runtime_base - saved_base`
- Scans all heap words; for each tagged pointer in range, adds `bias`
- Uses relocation mask: `(1<<fulltag_cons) | (1<<fulltag_nil) | (1<<fulltag_misc)`
- If bias = 0, the entire walk is skipped (or is a no-op)

**Where `__heap_base` comes from** ([wasm-no-wasi-libc.c:103-104](lisp-kernel/wasm-no-wasi-libc.c#L103-L104)):
```c
extern char __heap_base;
wasm_heap_ptr = align_up_uintptr((uintptr_t)&__heap_base, 16);
```

**Changes:**

1. **[rebuild-everything.sh](scripts/wasm/rebuild-everything.sh):** After kernel build, extract `__heap_base`:
   ```bash
   # Extract __heap_base from compiled kernel, align to 16 bytes
   RAW=$(wasm-objdump -x wasmcl.wasm | grep '__heap_base' | awk '{print $NF}')
   ALIGNED=$(( ($RAW + 15) & ~15 ))
   printf '%x' $ALIGNED > .heap-base
   export CCL_WASM_IMAGE_BASE=$(printf '%x' $ALIGNED)
   ```

2. **[xwasmfasload.lisp:76](xdump/xwasmfasload.lisp#L76):** Read from environment variable:
   ```lisp
   :image-base-address (or (let ((s (getenv "CCL_WASM_IMAGE_BASE")))
                             (and s (parse-integer s :radix 16 :junk-allowed t)))
                           #x10000000)  ; fallback for non-WASM builds
   ```

3. **[load-image.mjs](scripts/wasm/lib/load-image.mjs):** Remove relocation walk (bias = 0 always when using startup plan). The kernel-side `load_image_section()` in image.c already handles bias=0 efficiently.

**Constraint:** `__heap_base` shifts if kernel size changes. Must extract AFTER kernel build, BEFORE boot image build. Same build session required. `rebuild-everything.sh` already enforces this order.

---

## Phase 1: Verified Build

**Goal:** Rebuild with Phase 0 changes in place. Verify cold-boot init succeeds and FASL loading completes.

**Already implemented** (Phase 1a-1c) — no new code changes beyond Phase 0. Just rebuild:

```bash
scripts/wasm/rebuild-everything.sh
```

**Expected output:**
- `cold-boot-init: ok` (not `threw`)
- FASL loading begins and all 35 level-1 FASL files load
- `root.image` saved successfully
- `root.image.manifest.json` valid

**If new XNOFUN errors appear:** Add the missing function to the appropriate `wasm-*.lisp` file and rebuild. Phase 0A should have covered all 280+, but Murphy's Law applies.

---

## Phase 2: Build-Time Completeness + Launch Artifacts

**Goal:** Make the build emit a COMPLETE image (all const pools pre-installed) plus everything the launcher needs as flat, pre-resolved data.

### Phase 2A: Proactive Const Pool Installation

After all FASL loading completes, before saving the image, iterate ALL function table entries and install any uninstalled const pools.

**File:** [make-real-image.mjs](scripts/wasm/lib/make-real-image.mjs) (extend, after FASL loading, before image save ~line 1260)

```javascript
// Proactively install ALL const pools into the heap.
// After this, the saved image contains complete Lisp state.
// The launcher needs ZERO const pool data or installation logic.
trace("proactive-const-pool-install: starting...");
let installed = 0;
for (let entryIdx = 0; entryIdx < nextEntryIndex; entryIdx++) {
  if (hasConstPoolData(entryIdx) && !isConstPoolInstalled(entryIdx)) {
    installConstPoolBytes(entryIdx);
    installed++;
  }
}
trace(`proactive-const-pool-install: ${installed} pools installed, ${nextEntryIndex} total entries`);
```

**Why this works:** At this point in the build, the heap is fully initialized — all packages exist, all symbols are interned, all functions are defined. Const pool installation resolves Tag 1 (Symbol) via `intern`, Tag 4 (Function) via `fboundp`, Tag 7 (Package) by name — all of which succeed because the full standard library is loaded.

**What changes in the saved image:** ALL const pool data (symbols, strings, function vectors, etc.) is now in the heap snapshot. At launch, no const pool callbacks fire during startup.

### Phase 2B: Startup Plan + Module Binary

After saving root.image, emit two launch artifacts from data already in memory.

**File:** [make-real-image.mjs](scripts/wasm/lib/make-real-image.mjs) (extend, after image save)

#### `startup-plan.json` — Flat function table map

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-02-16T...",

  "memory": {
    "initialPages": 8192,
    "imageBase": "0x...",
    "imageSize": 12345678
  },

  "functionTable": {
    "size": 8387,
    "entries": [
      { "index": 0, "source": "subprims", "export": "_SPcallback" },
      { "index": 1, "source": "subprims", "export": "_SPthrow" },
      { "index": 5, "source": "kernel", "export": "_SPsome_kernel_export" },
      { "index": 132, "source": "modules", "offset": 0, "length": 1234, "export": "fn" },
      { "index": 133, "source": "modules", "offset": 1234, "length": 567, "export": "fn" }
    ]
  },

  "toplevelIndex": 8386,

  "artifacts": {
    "rootImage": { "sha256": "..." },
    "kernelWasm": { "sha256": "..." },
    "subprimsWasm": { "sha256": "..." },
    "modulesBin": { "sha256": "..." }
  }
}
```

**Key simplifications vs previous plan:**
- **No boot/runtime module distinction.** All compiled Lisp functions are just "modules" entries.
- **No const pool offsets.** Const pools are in the image. The launcher doesn't touch them.
- **No designator map.** Function designator resolution was a launch-time concept. With const pools pre-installed, designators are already resolved in the heap.
- Each entry is one of three sources: `subprims` (export from subprims.wasm), `kernel` (export from wasmcl.wasm), or `modules` (offset+length into modules.bin).

#### `modules.bin` — Flat uncompressed WASM module binary

Concatenation of ALL WASM module binaries (boot + runtime) in entry-index order. No headers, no framing, no compression.

```
[module_at_entry_132 bytes][module_at_entry_133 bytes]...[module_at_entry_8386 bytes]
```

The startup plan provides `{ offset, length }` for each entry. `make-real-image.mjs` already has all decompressed module bytes in memory; it writes them out sequentially and records offsets.

**Size estimate:** ~8255 modules × ~6KB average = ~50MB. Acceptable for development. For distribution, compress externally (gzip/brotli). The launcher reads uncompressed `modules.bin`.

---

## Phase 3: Deterministic Launcher

**Goal:** Launch = read plan → load image → instantiate modules → fill table → run. No scanning, parsing, resolving, or const pool work.

### Files DELETED

| File | Lines | Reason |
|------|-------|--------|
| [bootstrap-contract.mjs](scripts/wasm/lib/bootstrap-contract.mjs) | 163 | Semantic validation of startup functions. Replaced by artifact hash check. |
| [bootstrap-function-resolver.mjs](scripts/wasm/lib/bootstrap-function-resolver.mjs) | 975 | Symbol scanning + const pool walk to resolve function designators. Replaced by precomputed plan. |

### Files REWRITTEN

| File | Current | New (est.) | Change |
|------|---------|-----------|--------|
| [load-image.mjs](scripts/wasm/lib/load-image.mjs) | 1093 | ~200 | Plan-driven launcher. Delete all dynamic discovery, scanning, bundle parsing. |
| [microkernel.mjs](scripts/wasm/lib/microkernel.mjs) | 2054 | ~600 | Clean host ABI. Delete FASLOAD trace, V1 compat, debug cruft, unused ops. |

### Files SIMPLIFIED

| File | Current | Change |
|------|---------|--------|
| [ccl-loader.mjs](scripts/wasm/lib/ccl-loader.mjs) | 1159 | Gut startup logic. Keep ONLY runtime dynamic compilation support: `installCompiledModulesFromRegistry()`, on-demand const pool callback, function designator resolution. |

### Launcher Core Logic

```javascript
// === DETERMINISTIC LAUNCHER (load-image.mjs rewrite) ===

// 1. Read plan
const plan = JSON.parse(readFileSync("startup-plan.json"));
const modulesBin = readFileSync("modules.bin");
const imageBuf = readFileSync("root.image");
const kernelBytes = readFileSync("wasmcl.wasm");
const subprimsBytes = readFileSync("subprims.wasm");

// 2. Validate artifact hashes
for (const [name, expected] of Object.entries(plan.artifacts))
  assert(sha256(files[name]) === expected.sha256, `${name} hash mismatch`);

// 3. Create shared resources
const memory = new WebAssembly.Memory({ initial: plan.memory.initialPages });
const table = new WebAssembly.Table({ initial: plan.functionTable.size, element: "anyfunc" });

// 4. Load image — ZERO relocation (imageBase = __heap_base)
new Uint8Array(memory.buffer).set(imageBuf, plan.memory.imageBase);

// 5. Create microkernel (rewritten: clean host ABI)
const microkernel = createMicrokernel({ memory, table });

// 6. Instantiate kernel + subprims
const imports = createCclImports({ memory, table, microkernel });
const kernel = await WebAssembly.instantiate(kernelBytes, imports);
const subprims = await WebAssembly.instantiate(subprimsBytes,
  { ...imports, ccl: { ...imports.ccl, ...kernel.instance.exports } });

// 7. Fill subprims + kernel table entries
for (const e of plan.functionTable.entries.filter(e => e.source === "subprims"))
  table.set(e.index, subprims.instance.exports[e.export]);
for (const e of plan.functionTable.entries.filter(e => e.source === "kernel"))
  table.set(e.index, kernel.instance.exports[e.export]);

// 8. Parallel module compilation + table fill
const moduleEntries = plan.functionTable.entries.filter(e => e.source === "modules");
const compiled = await Promise.all(
  moduleEntries.map(e =>
    WebAssembly.compile(modulesBin.slice(e.offset, e.offset + e.length))));
for (let i = 0; i < compiled.length; i++) {
  const inst = await WebAssembly.instantiate(compiled[i], imports);
  table.set(moduleEntries[i].index, inst.exports[moduleEntries[i].export]);
}

// 9. Start
kernel.instance.exports.wasm_ccl_start_lisp();
```

**What's eliminated vs current launcher:**
- No JSON parsing of module bundle manifests
- No V2 binary index decoding or decompression
- No const pool installation (ALL pre-installed in image)
- No function designator resolution by scanning const pools
- No bootstrap contract semantic validation (replaced by SHA-256 hash check)
- No relocation walk (bias = 0)

**Step 8 detail — parallel compilation:** `Promise.all()` with ~8255 `WebAssembly.compile()` calls leverages V8's background compilation threads. If this overwhelms the engine, batch in chunks of 500:
```javascript
for (let i = 0; i < moduleEntries.length; i += 500) {
  const batch = moduleEntries.slice(i, i + 500);
  const compiled = await Promise.all(batch.map(e => WebAssembly.compile(...)));
  // instantiate + table.set for each...
}
```

### Microkernel Rewrite

The current 2054-line microkernel grew organically and carries significant cruft. Rewrite as a clean, minimal host ABI.

**Preserved (import contract — kernel expects these):**
- `kernel_request(opcode, payload_ptr, payload_len)` → request_id
- `kernel_poll(request_id)` → status
- `kernel_result(request_id)` → int32
- `kernel_copy_response(request_id, out_buf, out_cap)` → bytes_copied
- `kernel_drop_request(request_id)` → void
- `wasm_host_install_const_pool(entryIndex)` → callback (for runtime dynamic compilation)
- `wasm_host_resolve_function_designator_entry(name, pkg)` → entry_index (for runtime)

**Request handler — keep:**
- STREAM_WRITE, STREAM_READ, STREAM_OPEN, STREAM_CLOSE, STREAM_SEEK, STREAM_TRUNCATE
- FS_PROBE, FS_TRUENAME (others: stub for MVP-1)
- CAPS (capabilities query)
- LOG, TIME_NOW
- COMPILED_MODULES_REFRESH (for dynamic compilation)

**Delete:**
- FASLOAD trace decoding constants (lines 67-100, comment: "can be removed before shipping")
- V1 format compatibility paths
- NAMED_RO stream kind (build-time only, not needed at runtime)
- Debug scaffolding and diagnostic helpers
- Over-abstracted dispatch layers

**Stream kinds (simplified):**
- PIPE: stdin/stdout/stderr (pre-created at init)
- FILE: read-write file I/O (opened on demand)
- That's it. No NAMED_RO (build artifact only).

**Errno handling:** WASI-compatible values (EBADF=8, ENOENT=44, etc.). Set on the TCR or kernel global after each I/O operation. `%get-errno` reads it.

**Target: ~600 lines** (down from 2054).

### Dynamic Compilation Support (Post-Launch)

After startup, the running Lisp system can compile new functions. The runtime needs:

| Capability | Provider | When |
|-----------|----------|------|
| Compile new WASM module | `WebAssembly.compile()` + `instantiate()` | New function compiled |
| Grow function table | `table.grow()` + `table.set()` | New entry needed |
| Install const pool for new function | `wasm_host_install_const_pool()` callback | New function's pool requested |
| Replace existing function | `table.set(existingIndex, newFn)` | Function recompiled |
| Resolve function designator | `wasm_host_resolve_function_designator_entry()` callback | Const pool references named function |

These are retained in the simplified [ccl-loader.mjs](scripts/wasm/lib/ccl-loader.mjs). The startup plan describes INITIAL state only. The function table remains mutable after launch.

---

### Post-MVP2 Runtime Profiles (`dev` vs `fast`)

The deterministic startup contract above remains the baseline for mutable
runtime behavior (`dev` profile). Post-MVP2 adds a second saved-app profile for
finished applications (`fast` profile).

#### `dev` profile

- Keeps dynamic compilation support table exactly as defined above.
- Keeps mutable function-table behavior and runtime callback paths.
- Keeps generic call paths needed for open-world redefinition workflows.

#### `fast` profile

- Compiler payload is removed from the saved app image.
- Startup is closed-world for application modules: no startup-time dynamic
  compile/redefine work.
- Hot paths must use direct concrete calls (or compile-time expanded wrappers),
  not generic runtime function designator dispatch.

#### `call_indirect` gating (fast profile)

- The "zero `call_indirect`" rule is scoped to fast-profile application
  modules only and is enforced via opcode `0x11` scanning in build/test.
- Kernel/provider/bootstrap wasm artifacts may still contain `call_indirect`
  where required by the shared ABI (for example, `_SPfuncall` dispatch).

---

## Implementation Order

| Phase | What | Prereq | Effort | Net LOC Change |
|-------|------|--------|--------|---------------|
| **0A** | All WASM LAP bridge functions | None | ~2200 new lines | +2460 (11 new + 1 extended `.lisp`) |
| **0B** | Zero-relocation image base | None | ~20 lines | +15 (`xwasmfasload.lisp`, `rebuild-everything.sh`) |
| **1** | Verified build | 0A + 0B | Build time only | +0 |
| **2** | Proactive const pool install + launch artifacts | 1 | ~150 lines | +150 (`make-real-image.mjs`) |
| **3** | Deterministic launcher | 2 | ~1000 new, ~4000 deleted | **-2800** net (delete 1138, rewrite 3147 → 800) |
| **4** | Fast-profile save-app mode + invariants | 3 | Pipeline and validation work | TBD |

**Total net effect:** ~2460 new Lisp + 150 new JS - 2800 deleted JS ≈ **-190 net lines** of JS while gaining deterministic startup.

---

## Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|-----------|
| R1 | `%fixnum-ref`/`%fixnum-set` not compiler-intrinsic | Raw memory access breaks | Verify in wasm2.lisp. Add C exports if needed. |
| R2 | Hash function mismatch (`%pname-hash`, `%string-hash`) | Symbol lookup silently fails | Compare against native CCL for test strings |
| R3 | Undiscovered cold-load function dependencies | New XNOFUN at boot | All 280+ defined; should be covered |
| R4 | Bignum/float pure-Lisp too slow | Build takes longer | Acceptable per user: "can take days" |
| R5 | Frame walking needs WASM spill stack model | Backtrace/error handling broken | Implement based on spill stack layout |
| R6 | Proactive const pool install fails for some entries | Some pools missing in image | Log failures; fallback to on-demand for those entries |
| R7 | ~8255 parallel `WebAssembly.compile()` overwhelms V8 | Launch OOM or slow | Batch in chunks of 500 |
| R8 | `__heap_base` extraction fragile across toolchains | Wrong image base → relocation needed | Validate in build script; fail loudly on mismatch |
| R9 | `values` needs subprim dispatch, not simple `apply` | MV return protocol breaks | Route through `.SPvalues` subprim |

---

## Verification

### Phase 0
- `ls level-0/WASM/*.lafsl` shows all 12 compiled files
- `wasm-objdump -x wasmcl.wasm | grep __heap_base` value matches `:image-base-address`

### Phase 1
```bash
scripts/wasm/rebuild-everything.sh
```
- `cold-boot-init: ok`
- All 35 FASL files load
- `root.image` saved
- `root.image.manifest.json` valid

### Phase 2
- `proactive-const-pool-install:` log line in build output
- `build/wasm32/images/startup-plan.json` exists
- `jq '.functionTable.size'` → ~8387
- `jq '.functionTable.entries | length'` → ~8387
- `modules.bin` exists; size ≈ sum of all module lengths in plan
- All artifact SHA-256 hashes match actual file hashes

### Phase 3
```bash
node scripts/wasm/lib/load-image.mjs --startup-plan build/wasm32/images/startup-plan.json
```
- No const pool installation callbacks during startup
- No JSON bundle parsing
- No relocation walk
- REPL functional
- Measure and record launch time

---

## Reference: Const Pool Tag Encoding

For context on what proactive installation (Phase 2A) must handle:

| Tag | Type | Resolution | Heap Allocation |
|-----|------|-----------|-----------------|
| 1 | Symbol | `intern(name, package)` | Pointer to existing symbol |
| 2 | String | Direct | New string object |
| 3 | Vector | Element indices (pass 2) | New vector + forward-patch |
| 4 | Function | `fboundp(name, package)` | Pointer to existing function |
| 5 | Function-Vector | Slot indices (pass 2) | New vector + forward-patch |
| 6 | Fixnum | Direct | Boxed fixnum |
| 7 | Package | `find-package(name)` | Pointer to existing package |
| 8 | Cons | car_idx + cdr_idx (pass 2) | New cons + forward-patch |
| 9 | GVector | subtag + indices (pass 2) | New vector + forward-patch |
| 10 | Character | Direct | Boxed character |
| 11 | Single-Float | 32-bit IEEE754 | Misc object |
| 12 | Double-Float | hi + lo u32 | Misc object |
| 13 | Int64 | signed hi + lo | Bignum |
| 14 | UInt64 | unsigned hi + lo | Bignum |
| 15 | Bignum | digit count + u32[] | Bignum |
| 16 | Entry-Function | entry_index | Function vector with boxed index |

Tags 1, 4, 7 require interning/lookup — this is why proactive installation must happen AFTER the full standard library is loaded.

---

## Future Optimizations (Not In Scope)

- **V8 WASM code cache:** `WebAssembly.Module` serialization for faster second-launch
- **Module merging:** Combine compiled Lisp modules (Binaryen `wasm-merge`) to reduce instantiation count
- **Direct kernel imports:** Replace request/response buffer with direct WASM function imports for MVP-1 (breaks MVP-2 async compatibility)
- **Binary startup plan:** Replace JSON with binary format for marginally faster parsing
- **Streaming compilation:** `WebAssembly.compileStreaming()` for browser deployment
