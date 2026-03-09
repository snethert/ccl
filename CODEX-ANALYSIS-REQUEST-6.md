# Codex Read-Only Analysis Request: Float arithmetic produces garbage during cold-boot-init make-hash-table

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

**Output: Include a suggested solution (with code samples) in your report. Do NOT apply the solution.**

**Scope: Open-ended. Tell us everything you find, including things we haven't asked about.**

---

## What Changed Since CODEX-ANALYSIS-REQUEST-5

We implemented the plan from request 5 and fixed three bugs. Uncommitted changes across 8 files:

### Bug 1: Subprims nil_value vs lisp_nil mismatch (FIXED, turned out to be no-op)
- Added `wasm_nil()` cache + `wasm_set_subprims_nil` export in `wasm-subprims-provider.c`
- Replaced all 82 occurrences of `(LispObj)nil_value` → `wasm_nil()` in subprims
- Called from JS pipelines after image load
- **Finding**: `nil_value = lisp_nil = 0x04000001` — they're identical. Fix is harmless but a no-op.

### Bug 2: pending_throw silently cleared on Lisp-to-Lisp funcall (FIXED)
- `wasm_funcall_common` unconditionally cleared `pending_throw` at line 2651
- Now: C-to-Lisp calls (`!in_lisp`) clear it; Lisp-to-Lisp calls with pending_throw early-return
- This fixed `pending_throw=0x48 startup-step=0` → startup now reaches step 40+

### Bug 3: Missing pending_throw guard in `_SPmisc_alloc_init` (FIXED)
- After `_SPmisc_alloc()` signals XARRLIMIT and absorbs it, `_SPmisc_alloc_init` continued with garbage arg_z
- Added `if (wasm_pending_throw_p(tcr)) return;` after `_SPmisc_alloc()` call
- Prevents the cascading `_SPmisc_set: obj not misc` crash

### Build now succeeds
- cold-boot-init reaches step 40, XARRLIMIT is absorbed, cold-boot proceeds
- Image saves at 3.2 MiB
- **But launch hangs** — same XARRLIMIT at runtime, and without the build pipeline's error absorption, the process gets stuck

---

## Current Build Output (Relevant Excerpt)

```
[stage] setting subprims nil to 0x4000001
[stage] cold-boot-init starting (const-pool installs so far: 0, skipped: 0)
cold-boot-init: fn=0x0412d8be entry=0x00001168 (idx=1114)
MV2: v0=0x000000f0 v1=0x0fb96e7c
MAI: nst=0000002a e=0000027e st=0x00000128 cnt=0x1f72dd30 iv=0x00000033 axc=00000001
MA: st=0x00000128 cnt=0x1f72dd30
XARRLIMIT: subtag=0x0000004a count=0x1f72dd30 raw=0x07dcb74c nil=0x04000001
ksignalerr: absorbed=0x00000001 calls=0x00000001
cold-boot-init: pending_throw=0x00000040 startup-step=40
cold-boot-init: ok (infra ready, errors absorbed)
[stage] --no-fasload: L1 baked into boot image, skipping FASL loading
[save-image-diag] persisted image size: 3321872 bytes (3.2 MiB)
```

---

## The Problem

`make-hash-table` at cold-boot-init step 40 calls `compute-hash-size` which returns a garbage second value (vector-size). This garbage propagates to `%cons-nhash-vector` → `%alloc-misc` → `_SPmisc_alloc_init` → XARRLIMIT.

### Diagnostic Decode

| Diagnostic | Value | Meaning |
|-----------|-------|---------|
| `MV2: v0=0xf0 v1=0x0fb96e7c` | First `wasm_return_values2` call | `compute-hash-size` returns `(values 60 0x0fb96e7c)`. v0=60 (boxed, correct new-size). v1=0x0fb96e7c (boxed fixnum ≈ 66M, **garbage**) |
| `MAI: e=0000027e` | Entry 638 | `%CONS-NHASH-VECTOR` (confirmed via startup plan) |
| `MAI: st=0x128` | box_fixnum(74) | subtag_hash_vector (correct) |
| `MAI: cnt=0x1f72dd30` | box_fixnum(131,898,700) | Element count (**garbage**, should be ~228) |
| `MAI: iv=0x33` | immediate | Unbound marker = `free-hash-marker` (correct) |
| `MAI: axc=00000001` | wasm_set_arg_x calls | Exactly 1 call to `wasm_set_arg_x` — the compiled code DID set arg_x to this garbage value |
| `ksignalerr: absorbed=1 calls=1` | | This is the ONLY error — no earlier absorbed errors |

### Traced Computation

The call chain:
```
%run-cold-boot-init (step 40)
  → (make-hash-table :test 'eq)        ; l0-hash.lisp:1294
    → (setq rehash-threshold (/ 1.0 (max 0.01 rehash-threshold)))  ; line 464
    → (compute-hash-size size 0 rehash-threshold)                    ; line 498
      → (ceiling (* new-size rehash-ratio))                           ; line 521
      → (%hash-size result)
      → (values new-size vector-size)   ; ← vector-size is GARBAGE
    → (%cons-nhash-vector total-size flags)                          ; line 507
      → (%alloc-misc count subtag initval)
        → _SPmisc_alloc_init → _SPmisc_alloc → XARRLIMIT
```

The garbage value 0x0fb96e7c is the `vector-size` (second return value from `compute-hash-size`). Working backwards:

```
%cons-nhash-vector receives: size = 0x0fb96e7c (boxed ≈ 66M)
count = (+ (+ size size) $nhash.vector_overhead)
      = 2 * 0x0fb96e7c + 56
      = 0x1f72dd30 (matches MAI cnt)
```

So `compute-hash-size` returns garbage as its second value. Inside `compute-hash-size`:

```lisp
(defun compute-hash-size (size rehash-size rehash-ratio)
  ;; size=60, rehash-size=0, rehash-ratio=<double-float ~1.176>
  (let* ((new-size (max 30 (%i+ 60 0))))   ; = 60, confirmed by MV2 v0=0xf0
    (let ((vector-size (%hash-size (max (+ 62) (ceiling (* 60 rehash-ratio))))))
      (values new-size vector-size))))
```

`new-size=60` is correct (v0=0xf0=box(60)). The garbage is in `vector-size`, which comes from `%hash-size(...)`. The input to `%hash-size` is `(max 62 (ceiling (* 60 rehash-ratio)))`.

If `(ceiling (* 60 rehash-ratio))` returns garbage, it propagates through `max` and `%hash-size`.

### What `(* 60 rehash-ratio)` involves

`rehash-ratio` = `(/ 1.0 0.85)` ≈ 1.176 (a boxed double-float on the heap).

`(* 60 1.176)` is fixnum × double-float. The generic `*` function must:
1. Detect the type combination (fixnum × double-float)
2. Convert 60 to double-float 60.0
3. Multiply 60.0 × 1.176 = 70.59
4. Return a boxed double-float

Then `(ceiling 70.59)` must:
1. Extract the f64 value
2. Apply ceiling → 71.0
3. Convert to fixnum 71 (boxed: 0x11C)

The expected result is 71. The actual result is garbage ≈ 66M.

### The garbage is deterministic

The value 0x0fb96e7c has been consistent across the last 3+ builds (same code). Earlier builds (before the nil/pending_throw fixes) showed 0x088ae710 (different garbage). The determinism rules out random uninitialized memory — this is a computed value that's consistently wrong.

---

## What We Want Investigated

### 1. Trace the generic `*` dispatch for fixnum × double-float on WASM

How does `(* 60 <double-float>)` compile and execute on WASM? The compiler might:
- (a) Open-code it if types are known → `%fixnum-to-double` + `%double-float*-2`
- (b) Call the generic `*` via funcall if types are unknown

Since `rehash-ratio` is an untyped function parameter, option (b) is likely. Trace the generic `*` function's dispatch chain for this type combination. Does it reach `%double-float*-2`? Does the fixnum→double conversion work?

### 2. Check `wasm2-emit-box-double` interaction with `_SPmisc_alloc`

`wasm2-emit-box-double` (wasm2.lisp:5171) allocates a double-float object via `wasm2-emit-misc-alloc-call-known-constants`, then stores the f64 at `misc-dfloat-offset` (=6). The allocation goes through a fast-path C function (`wasm2-runtime-misc-alloc-import-index`).

Questions:
- What is `wasm2-runtime-misc-alloc-import-index`? What C function does it call?
- Does this C allocator return a correctly tagged pointer?
- After allocation, `f64.store offset=6` stores the value. Is offset 6 correct for a 32-bit target double-float? (header=4 bytes + pad=4 bytes + f64=8 bytes; offset from tagged pointer = -2 + 8 = 6 ✓)
- When `wasm2-emit-unbox-double` later reads with `f64.load offset=6`, does it get the right value?

### 3. Investigate `wasm2-emit-misc-alloc-call-known-constants` and `wasm2-with-spilled-locals`

The fast-path allocator in `wasm2-emit-misc-alloc-call-known-constants` (wasm2.lisp:4221) uses `wasm2-with-spilled-locals` to preserve WASM locals across the C call. If this spilling is incorrect (wrong locals spilled, or spill/restore order wrong), locals could be corrupted after the allocation.

The box-double sequence is:
```
f64-value on WASM stack
→ local.set val-temp      (save f64)
→ misc-alloc-known(subtag, count)  ← C call, locals spilled
→ local.set obj-temp      (save allocated obj)
→ local.get obj-temp
→ local.get val-temp      ← IS THIS CORRECT after spill/restore?
→ f64.store offset=6
→ local.get obj-temp      (return obj)
```

If `val-temp` (the f64 local) is NOT properly spilled/restored across the C allocation call, the f64 store would write garbage into the double-float object. Then unboxing it later returns garbage.

**THIS IS OUR PRIMARY HYPOTHESIS.** The `wasm2-with-spilled-locals` mechanism might not handle f64 locals correctly — it might only spill i32 locals, silently losing f64 values across C calls.

### 4. Check how `ceiling` handles double-float → fixnum conversion on WASM

`(ceiling 70.59)` should return fixnum 71. Trace the generic `ceiling` function's dispatch for double-float input. Does it use `%unary-truncate` or `%double-float-ceiling`? How is the f64→i32 conversion done?

### 5. Check const pool entries for `make-hash-table`

The literals `1.0`, `0.85`, `0.01` in `make-hash-table` are double-float constants stored in the function's const pool. Verify:
- What entry index is `make-hash-table`?
- Is its const pool installed? (boot modules should have pools installed)
- Are the const pool slots for these double-float literals valid?

### 6. Anything else

Read the code freely and report what you find. The root cause is: `compute-hash-size` returns garbage as its second value when `rehash-ratio` is a double-float. Something in the float arithmetic pipeline on WASM is broken.

---

## Key Files

| File | What's There |
|------|-------------|
| `level-0/l0-hash.lisp` | `make-hash-table` (line 431), `compute-hash-size` (line 516), `%hash-size` (line 529), `%cons-nhash-vector` (line 1942) |
| `compiler/WASM/wasm2.lisp` | `wasm2-%double-float*-2` (line 608), `wasm2-%double-float/-2` (line 618), `wasm2-%fixnum-to-double` (line 537), `wasm2-emit-box-double` (line 5171), `wasm2-emit-unbox-double` (line 5145), `wasm2-emit-misc-alloc-call-known-constants` (line 4221), `wasm2-with-spilled-locals` (search for it), `wasm2-values` (line 3249), `wasm2-multiple-value-bind` (line 3337), `wasm2-%alloc-misc` (line 3444) |
| `compiler/WASM/wasm-arch.lisp` | `misc-dfloat-offset` (line 252 = 6), `misc-data-offset` (line 251 = 2), `misc-header-offset` (line 249 = -2) |
| `lisp-kernel/wasm-kernel-stubs.c` | `wasm_return_values2` (line 1933), `wasm_get_mv` (line 2010), `wasm_restore_vsp` (line 2070), `wasm_set_arg_x` (line 1663), `wasm_funcall_common` (line 2630), `wasm_spill_push/pop` (line 2147) |
| `lisp-kernel/wasm-subprims-provider.c` | `_SPmisc_alloc` (line 3628), `_SPmisc_alloc_init` (line 3712), `wasm_call_function_or_symbol` (line 2694), `wasm_funcall_nfn` (line 2793) |
| `level-0/nfasload.lisp` | `%run-cold-boot-init` (line 1268), step 40 hash table creation (line 1293) |
| `scripts/wasm/lib/make-real-image.mjs` | Build pipeline, cold-boot-init invocation |
| `xdump/hashenv.lisp` | `$nhash.vector_overhead = 14` (line 53), `secondary-keys = #(3 5 7 11 13 17 19 23)` (line 23) |
| `level-0/l0-numbers.lisp` | Generic `*`, `/`, `ceiling` dispatch |

---

## Git Context

```
Branch: wasm-port
HEAD: 8317da5f wasm: defer runtime const-pool install to after cold-boot-init

Uncommitted changes (8 files):
 M lisp-kernel/pmcl-kernel.c              (advance C heap past purespace)
 M lisp-kernel/wasm-kernel-stubs.c        (funcall_common pending_throw fix, MV2 diagnostic, arg_x counter)
 M lisp-kernel/wasm-no-wasi-libc.c        (wasm_advance_malloc_past)
 M lisp-kernel/wasm-subprims-provider.c   (wasm_nil() cache, pending_throw guards, MAI diagnostic)
 M lisp-kernel/wasm32/subprims/Makefile   (--global-base=10485760)
 M scripts/wasm/lib/load-image.mjs        (wasm_set_subprims_nil call)
 M scripts/wasm/lib/make-real-image.mjs   (wasm_set_subprims_nil, installConstPools: true)
 M scripts/wasm/rebuild-everything.sh     (subprims layout gap validation)
```

---

## Specific Questions for Codex

1. **Find `wasm2-with-spilled-locals`** and determine: does it spill f64 locals? Or only i32? If only i32, every `box-double` call would lose the f64 value across the allocation, and the stored double-float would contain whatever was previously in the f64 local — i.e., **deterministic garbage from a previous f64 operation in the same WASM function**.

2. **Find `wasm2-runtime-misc-alloc-import-index`** — what C function does this resolve to? Is it `wasm_misc_alloc_internal` or something else? Does it modify WASM locals (it shouldn't, since it's a C function called from WASM)?

3. **If f64 spilling IS the bug**, propose a fix: `wasm2-with-spilled-locals` should also spill f64 locals (and f32 locals) to the spill stack, or use a separate f64 spill mechanism. Show code samples for the fix.

4. **If f64 spilling is NOT the bug**, what else could cause `compute-hash-size` to return deterministic garbage as its second value?
