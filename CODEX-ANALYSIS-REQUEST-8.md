# Codex Read-Only Analysis Request: `_SPbuiltin_times` dispatches to `*-2` but result is still garbage

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

**Output: Include a suggested solution (with code samples) in your report. Do NOT apply the solution.**

**Scope: Open-ended. Tell us everything you find, including things we haven't asked about.**

---

## What Changed Since CODEX-ANALYSIS-REQUEST-7

Two fixes applied:
1. **`mul2`/`add2`/`sub2` → builtin subprims** (from request 6) — CONFIRMED working: no boot module imports `wasm_return_fixnum_mul` anymore. All modules use `wasm_call_subprim`.
2. **Spill stack restore-before-pending** (from request 7) — moved `restore-locals` before `pending-throw` check in `wasm2-emit-call-with-pending`.

### Build result
**The error persists with IDENTICAL state dump.** The same `ksignalerr` fires at cold-boot-init step 40 with byte-identical register values, spill counters, and vstack contents. This proves:
- The compiled code IS different (no more `wasm_return_fixnum_mul` imports)
- But the subprim dispatch path produces the same garbage
- The spill imbalance (5619/4852) is NOT caused by the `call-with-pending` leak — it's normal call depth at the point of error

---

## State Dump (identical across last 2 builds)

```
=== STATE DUMP: ksignalerr ===
  imm0     = 0x00000000
  imm1     = 0x000000c8
  nargs    = 0x0000000c
  arg_z    = 0x0fb96e4d
  arg_y    = 0x0ff96e5e
  arg_x    = 0x00000274
  nfn      = 0x04117546
  vsp      = 0x0222afd0
  spill: sp=0x0224ab04 base=0x0222b700 limit=0x0224b700 depth=767
  catch_top=0x00000000 db_link=0x00000000 pending_throw=0x00000000
  VSP=0x0222afd0 top: 0x0fb96e66 0x000000f0 0x0fb96e66 0x000000f0
  spill_push=5619 spill_pop=4852
  last_cpr: e=836 s=0 val=0x0411755e
=== END STATE DUMP ===
  expected=0x0fb96e4d ft=5 (0x0411962e 0x00000080)
ksignalerr: absorbed=0x00000001 calls=0x00000001
cold-boot-init: pending_throw=0x00000040 startup-step=40
```

### Register decode

| Register | Value | Meaning |
|----------|-------|---------|
| `arg_x` | `0x274 = box_fixnum(157)` | WASM_XWRONGTYPE error code |
| `arg_y` | `0x0ff96e5e` (ft=6) | Datum — NOT a valid Lisp object (fulltag=6=immheader) |
| `arg_z` | `0x0fb96e4d` (ft=5) | Expected type specifier — also garbage (ft=5=fulltag_misc, ~264MB) |
| `nargs` | `0x0c = 12` | Nargs at error point |
| `nfn` | `0x04117546` | Current function (in dynamic heap, valid range) |
| `last_cpr` | `e=836` | `INTEGER-LENGTH` |
| vstack | `0x0fb96e66 0xf0 0x0fb96e66 0xf0` | Garbage and `box_fixnum(60)` alternating |

---

## The Trace (what we now know)

### The code path

```
%run-cold-boot-init (step 40)
  → make-hash-table :test 'eq
    → (setq rehash-threshold (/ 1.0 (max 0.01 rehash-threshold)))  ; line 464
    → (compute-hash-size size 0 rehash-threshold)                    ; line 498
      → (* new-size rehash-ratio)                                     ; line 521
```

### How `(* new-size rehash-ratio)` compiles NOW

Compiler macro: `(* a b)` → `(*-2 a b)`
nx1 transform: `*-2` → `mul2` acode
Acode rewrite: `new-size` is fixnum, `rehash-ratio` is unknown → stays `mul2`
WASM backend: `wasm2-mul2` → `wasm2-emit-builtin-subprim-binary-call '.SPbuiltin-times`
Emission:
```
eval new-size → WASM stack
eval rehash-ratio → WASM stack
call wasm_set_arg_y  (pop rehash-ratio → arg_y)
call wasm_set_arg_z  (pop new-size → arg_z)
spill-locals
call wasm_call_subprim(box_fixnum(3))  ; .SPbuiltin-times
restore-locals
call wasm_get_arg_z → push result
```

### What `_SPbuiltin_times` does at runtime

```c
void _SPbuiltin_times(void) {
  LispObj a = wasm_reg(tcr, arg_z);   // new-size (fixnum 60 = 0xf0)
  LispObj b = wasm_reg(tcr, arg_y);   // rehash-ratio (double-float pointer)
  if (tag_of(a) == tag_fixnum && tag_of(b) == tag_fixnum) {
    // FAST PATH: both fixnum → fixnum multiply
    // SKIPPED because b is double-float
  }
  wasm_call_builtin(tcr, WASM_BUILTIN_TIMES, 2);
}
```

### What `wasm_call_builtin` does

```c
void wasm_call_builtin(TCR *tcr, signed_natural index, signed_natural nargs_count) {
  LispObj fn = wasm_builtin_function(index);
  // fn = %builtin-functions%[2] = symbol *-2

  // Swap arg_z ↔ arg_y for Lisp calling convention
  LispObj tmp = wasm_reg(tcr, arg_z);       // tmp = 0xf0 (new-size)
  wasm_set_reg(tcr, arg_z, wasm_reg(tcr, arg_y));  // arg_z = rehash-ratio
  wasm_set_reg(tcr, arg_y, tmp);            // arg_y = 0xf0

  wasm_set_nargs_count(tcr, 2);
  wasm_call_function_or_symbol(tcr, fn);    // call *-2 with (arg_y=0xf0, arg_z=rehash-ratio)
}
```

After the swap: `arg_y = new-size (fixnum 60)`, `arg_z = rehash-ratio (double-float)`.
This matches Lisp convention: `(funcall *-2 arg_y arg_z)` = `(*-2 60 rehash-ratio)`.

### What happens next: `*-2` execution

`*-2` is defined in `l0-numbers.lisp:715`. It dispatches on argument types. For fixnum × double-float, it should:
1. Convert fixnum 60 to double-float 60.0
2. Multiply 60.0 × 1.176... ≈ 70.59
3. Return boxed double-float ≈ 70.59

But instead, a type error is signaled deep in the dispatch chain (last_cpr=836=`INTEGER-LENGTH`).

---

## What We Want Investigated

### 1. Trace `*-2` dispatch for (fixnum × double-float)

`*-2` is at `l0-numbers.lisp:715`. Read this function and trace the dispatch for `(fixnum . double-float)`. Which branch does it take? Does it call `%fixnum-to-double` and then `%double-float*-2`? Or does it go through a different path?

### 2. Why does `INTEGER-LENGTH` (entry 836) appear?

`last_cpr: e=836` means the last const-pool reference was from entry 836 (`INTEGER-LENGTH`). Why would `(* 60 double-float)` need `INTEGER-LENGTH`? Trace the call chain from `*-2` to `INTEGER-LENGTH` for this type combination.

Is the `*-2` dispatch going through bignum/integer multiply paths instead of float paths? That would be wrong and would explain the type error.

### 3. Check `rehash-ratio` itself

Before `*-2` is called, `rehash-ratio` should be a valid double-float object at some heap address. But after the arg swap, `arg_z = rehash-ratio`. Is this a valid tagged double-float pointer?

The value `0x0fb96e4d` appears in `arg_z` at the time of error. Is this the swapped `rehash-ratio`? If `rehash-ratio` was `0x0fb96e4d` (ft=5=fulltag_misc), that COULD be a valid double-float pointer IF the address is valid. But `0x0fb96e4d` is at ~264MB, far beyond the dynamic heap (`0x4110000–0x4378360`).

So either:
- **`rehash-ratio` is already garbage before `*-2` is called** — meaning `(/ 1.0 0.85)` returned garbage
- OR **the registers were corrupted between the eval and the subprim call**

### 4. Trace `(/ 1.0 0.85)` which produces `rehash-ratio`

`make-hash-table` line 464:
```lisp
(setq rehash-threshold (/ 1.0 (max 0.01 rehash-threshold)))
```

Where `rehash-threshold` defaults to `$nhash-default-rehash-threshold` = 0.85 (a double-float). This computation: `1.0 / 0.85 ≈ 1.176`.

`(/ 1.0 0.85)` compiles as `(/-2 1.0 0.85)` → `div2` → `wasm2-div2` → `.SPbuiltin-div`. The `_SPbuiltin_div` fast path checks fixnum — both are floats, so it falls through to `wasm_call_builtin(WASM_BUILTIN_DIV, 2)` → `/-2` (Lisp function).

Does this division succeed? If NOT, its garbage result becomes `rehash-ratio`, which then causes the `*-2` type error.

**Question**: How do float constants `1.0` and `0.85` appear in compiled code? Are they:
- (a) Inline WASM `f64.const` instructions that get boxed at runtime?
- (b) Const pool references to pre-allocated double-float objects?
- (c) Something else?

If they're const pool references, the const pool must be installed for `make-hash-table`'s entry (581) before cold-boot-init. Is it?

### 5. Check `(max 0.01 rehash-threshold)` compilation

Before the division, `(max 0.01 rehash-threshold)` is computed. `max` with floats also involves generic arithmetic. If THIS produces garbage, the division gets garbage input.

### 6. What is `wasm_call_subprim` (the import)?

`wasm_call_subprim` is the kernel import called by the WASM module to invoke a subprim. In `wasm-kernel-stubs.c`, find this function. What does it do? Does it:
- Read the subprim fixnum from the WASM stack?
- Look up the subprim in the function table?
- Call it?
- Handle errors?

If `wasm_call_subprim` has a bug (e.g., wrong table lookup, or corrupts registers), all subprim calls would fail.

### 7. Verify the full `wasm2-emit-builtin-subprim-binary-call` code path

The compiled code for `(* new-size rehash-ratio)` should be:
```
;; eval new-size (fixnum variable) → push onto WASM operand stack
;; eval rehash-ratio (variable) → push onto WASM operand stack
call $wasm_set_arg_y   ;; pop rehash-ratio → TCR.arg_y
call $wasm_set_arg_z   ;; pop new-size → TCR.arg_z
;; spill locals
i32.const 12           ;; box_fixnum(3) = .SPbuiltin-times
call $wasm_call_subprim
;; restore locals
call $wasm_get_arg_z   ;; push result
```

Verify that `wasm_call_subprim(12)` correctly maps `box_fixnum(3)` → `.SPbuiltin-times`. What is the mapping mechanism? `wasm_call_subprim` receives a boxed fixnum and must find the right C function to call.

### 8. Anything else

The state dump being identical across builds with different code is the key puzzle. The code path changed (confirmed: no more `wasm_return_fixnum_mul` imports) but the error is exactly the same. This means the garbage is produced BEFORE `*-2` is called — either in evaluating the arguments to `*`, or in a computation upstream (`/`, `max`, const pool load).

---

## Key Files

| File | What's There |
|------|-------------|
| `level-0/l0-numbers.lisp` | `*-2` (715), `/-2` (828), `+-2` (510), generic dispatch |
| `level-0/l0-hash.lisp` | `make-hash-table` (431), `compute-hash-size` (516) |
| `compiler/WASM/wasm2.lisp` | `wasm2-mul2` (257), `wasm2-div2` (289), `wasm2-emit-builtin-subprim-binary-call` (262), `wasm2-emit-call-subprim` (4938), `wasm2-emit-call-with-pending` (5958) |
| `lisp-kernel/wasm-subprims-provider.c` | `_SPbuiltin_times` (4335), `_SPbuiltin_div` (4354), `wasm_call_builtin` (740), `wasm_builtin_function` (706) |
| `lisp-kernel/wasm-kernel-stubs.c` | `wasm_call_subprim` (search), `wasm_set_arg_z`, `wasm_set_arg_y`, `wasm_get_arg_z`, `wasm_spill_push/pop` |
| `level-0/nfasload.lisp` | `%run-cold-boot-init` (1268), step 40 (1285) |
| `xdump/xfasload.lisp` | `%builtin-functions%` vector (325) |
| `scripts/wasm/lib/make-real-image.mjs` | Module install and cold-boot-init call order |

---

## Git Context

Same as request 7 (9 uncommitted modified files).

---

## Specific Questions for Codex

1. Is the garbage `0x0fb96e4d` in `arg_z` at error time equal to `rehash-ratio` (the double-float result of `(/ 1.0 0.85)`)? Or has it been corrupted since?

2. Does `wasm_call_subprim` correctly dispatch `box_fixnum(3)` to `_SPbuiltin_times`? What's the table lookup mechanism?

3. What are the float constants `1.0`, `0.85`, `0.01` in the compiled `make-hash-table` — inline `f64.const` or const pool refs? If const pool refs, is the pool for entry 581 installed?

4. Could the error be in `(max 0.01 rehash-threshold)` rather than `(* new-size rehash-ratio)`? `max` with float args also dispatches through generic comparison.

5. Does `wasm_call_function_or_symbol` correctly handle calling a SYMBOL (not a function)? The `%builtin-functions%` vector contains SYMBOLS (`*-2`, `/-2`, etc.), not function objects. `wasm_call_function_or_symbol` must resolve the symbol's fcell to get the function.
