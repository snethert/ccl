# Codex Read-Only Analysis Request: `*-2` XWRONGTYPE on valid single-floats — why?

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

**Output: Include a suggested solution (with code samples) in your report. Do NOT apply the solution.**

**Scope: Open-ended. Tell us everything you find, including things we haven't asked about.**

---

## What Changed Since CODEX-ANALYSIS-REQUEST-8

Added diagnostic logging to `_SPbuiltin_gt`, `_SPbuiltin_div`, `_SPbuiltin_times`, `_SPbuiltin_plus`, `_SPbuiltin_minus` in `wasm-subprims-provider.c`. Logs arg values, fulltags, and **header subtags** of misc-tagged args when the fixnum fast path is not taken. Also logs results after `wasm_call_builtin` returns.

---

## Diagnostic Output (COMPLETE)

```
[stage] cold-boot-init starting (const-pool installs so far: 0, skipped: 0)
cold-boot-init: fn=0x0412d8be entry=0x00001168 (idx=1114)

BLT GT    z=0x0fb96e9e y=0x0fb96ea6 ft_z=6 ft_y=6 st_z=0x0f st_y=0x0f throw=0x00000000
BLT-RET idx=00000006 z=0x04000001 ft=00000001 throw=0x00000000
BLT-RET idx=00000009 z=0x0400000e ft=00000006 throw=0x00000000

BLT GT    z=0x0fb96ea6 y=0x0fb96e96 ft_z=6 ft_y=6 st_z=0x0f st_y=0x0f throw=0x00000000
BLT-RET idx=00000006 z=0x04000001 ft=00000001 throw=0x00000000
BLT-RET idx=00000009 z=0x0400000e ft=00000006 throw=0x00000000
BLT-RET idx=00000008 z=0x0400000e ft=00000006 throw=0x00000000

BLT GT    z=0x0fb96e7e y=0x0fb96ea6 ft_z=6 ft_y=6 st_z=0x0f st_y=0x0f throw=0x00000000
BLT-RET idx=00000006 z=0x04000001 ft=00000001 throw=0x00000000

BLT DIV   z=0x0fb96e86 y=0x0fb96ea6 ft_z=6 ft_y=6 st_z=0x0f st_y=0x0f throw=0x00000000
BLT-RET idx=00000003 z=0x0fb96e76 ft=00000006 throw=0x00000000

BLT TIMES z=0x000000f0 y=0x0fb96e76 ft_z=0 ft_y=6 st_y=0x0f throw=0x00000000

=== STATE DUMP: ksignalerr ===
  imm0     = 0x00000000
  imm1     = 0x000000c8
  nargs    = 0x0000000c
  arg_z    = 0x0fb96e4d
  arg_y    = 0x0ff96e5e
  arg_x    = 0x00000274
  vsp      = 0x0222afd0
  spill: sp=0x0224ab04 base=0x0222b700 limit=0x0224b700 depth=767
  VSP=0x0222afd0 top: 0x0fb96e66 0x000000f0 0x0fb96e66 0x000000f0
  spill_push=5619 spill_pop=4852
  last_cpr: e=836 s=0 val=0x0411755e
=== END STATE DUMP ===
  expected=0x0fb96e4d ft=5 (0x0411962e 0x00000080)
ksignalerr: absorbed=0x00000001 calls=0x00000001

BLT-RET idx=00000002 z=0x0fb96e66 ft=00000006 throw=0x00000040

cold-boot-init: pending_throw=0x00000040 startup-step=40
cold-boot-init: ok (infra ready, errors absorbed)
```

---

## What We Now Know For Certain

### 1. All float objects are valid single-floats

Every non-fixnum argument to GT, DIV, and TIMES has `st=0x0f` = `subtag_single_float`. These are properly allocated single-float objects in an extended heap segment at ~264MB (valid WASM linear memory).

### 2. GT and DIV succeed with single-float args

- `(> sfloat sfloat)` → returns NIL (`0x04000001`). No error.
- `(/ sfloat sfloat)` → returns new single-float (`0x0fb96e76`, st=0x0f). No error.

Both `>-2` and `/-2` correctly dispatch on single-float arguments and produce correct results.

### 3. TIMES fails with (fixnum × single-float)

`_SPbuiltin_times` correctly detects non-fixnum args and falls through to `wasm_call_builtin(WASM_BUILTIN_TIMES, 2)`. `wasm_call_builtin` swaps args (WASM→Lisp convention), then calls `wasm_call_function_or_symbol` with the `*-2` symbol from `%builtin-functions%[2]`. Somewhere inside `*-2`'s Lisp dispatch, XWRONGTYPE is signaled.

### 4. The BLT-RET lines show nested builtin calls

The `BLT-RET idx=00000009` (LE) and `BLT-RET idx=00000008` (GE) lines appear without corresponding `BLT` entry lines. These are calls made by compiled Lisp code INSIDE the `>-2` dispatch — they go through `_SPbuiltin_le` / `_SPbuiltin_ge` which take the fixnum fast path (both args are fixnums at that point), so no `BLT` log is emitted. The return logging fires because `wasm_builtin_diag_count > 0`.

### 5. `0x0400000e` (ft=6) is T

LE/GE return `0x0400000e`. This is `fulltag_misc` tagged, at untagged address `0x04000008`. This is in the NIL page area. It's the T symbol.

### 6. Entry indices from startup plan

| Entry | Function |
|-------|----------|
| 785 | `*-2` |
| 788 | `*-2-INTO` |
| 750 | `%SHORT-FLOAT*-2!` |
| 746 | `%DOUBLE-FLOAT*-2!` |
| 767 | `>-2` |
| 791 | `/-2` |
| 836 | `(FINALIZE-INHERITANCE (STD-CLASS))` — NOT INTEGER-LENGTH! |

**Correction**: Entry 836 is `FINALIZE-INHERITANCE`, not `INTEGER-LENGTH` as previously assumed. The `last_cpr: e=836` at error time means the last const-pool reference was from a CLOS function, NOT from arithmetic. This changes the interpretation — the error might originate in a completely different context.

Wait — `last_cpr` tracks the last const-pool reference during the current WASM function execution. If the error occurs deep inside `*-2` dispatch, the `last_cpr` value reflects whatever function most recently performed a const-pool lookup. `FINALIZE-INHERITANCE` might have been called earlier in cold-boot-init before step 40.

---

## What We Don't Know

### The central mystery: why does `*-2` fail for (fixnum × single-float)?

The `*-2` function in `l0-numbers.lisp:715` dispatches via `*-2-into` (line 720). For fixnum × short-float (line 767):

```lisp
(fixnum (number-case y
          ...
          (short-float (sfloat-rat * y x))
          ...))
```

The `sfloat-rat` macro on 32-bit (line 50-59) expands to:
```lisp
(let ((f2 (%short-float FIXNUM (%make-sfloat))))
  (%short-float*-2! SHORT-FLOAT f2 f2))
```

This chain involves:
1. `(%make-sfloat)` — allocates via `%alloc-misc` (arch macro, line 834-835 of wasm-arch.lisp)
2. `(%short-float fixnum result)` — calls `%fixnum-sfloat` → `%int-to-sfloat!` (wasm-float.lisp:372-391)
3. `(%short-float*-2! sfloat sfloat result)` — destructive multiply

`%short-float*-2!` is defined at `l0-numbers.lisp:124` as:
```lisp
#-64-bit-target
(defun %short-float*-2! (x y result)
  (declare (short-float x y result))
  (%setf-short-float result (the short-float (* x y))))
```

**The `(* x y)` inside is a RECURSIVE call to generic `*`!** The compiler should optimize it to `%short-float*-2` (the non-destructive vinsn) because both x and y are declared `short-float`. The acode rewriter (`acode-rewrite.lisp:336-339`) checks `(subtypep t1 'single-float)` — but only if `*acode-rewrite-trust-declarations*` is true.

**`*acode-rewrite-trust-declarations*` defaults to `nil`** (line 23 of `acode-rewrite.lisp`). It's only set to `t` when the compilation policy has `trust-declarations` enabled (`$decl_trustdecls`). The `*-2-into` function has `(declare (optimize (speed 3)(safety 0)))` **commented out** (line 721).

### Hypothesis: `%short-float*-2!` compiles with untrusted declarations

If the compiler doesn't trust the `(declare (short-float x y result))`, then `(* x y)` inside `%short-float*-2!` compiles as generic `mul2` → `wasm2-mul2` → `.SPbuiltin-times` → `*-2` → `*-2-into` → ... → `%short-float*-2!` → infinite recursion.

On WASM, `wasm_call_function_or_symbol` has a **depth limit of 800** (line 2805 of `wasm-subprims-provider.c`). When depth exceeds 800, it sets `pending_throw = 1` and returns. This would cause the recursive call chain to unwind, and at some point an XWRONGTYPE error might surface from a corrupted state.

But wait — the error is XWRONGTYPE, not a depth-related error. And `pending_throw` is `0x00000000` when TIMES is called. The first error absorbed is this XWRONGTYPE at step 40 (`absorbed=1, calls=1`).

---

## What We Want Investigated

### 1. Does `%short-float*-2!` (entry 750) contain a recursive call to `*-2`?

Decompile or analyze the compiled WASM code for entry 750. Does it:
- (a) Use inline `f32.mul` (meaning the compiler trusted declarations → `%short-float*-2` vinsn) — this is correct
- (b) Call `.SPbuiltin-times` via `wasm_call_subprim_fixnum(12)` — this is a recursive generic `*` call → infinite recursion

Check: does entry 750's WASM module import `wasm_call_subprim_fixnum`? If yes, it's making subprim calls, which means the compiler did NOT optimize the `(* x y)` to inline float ops.

### 2. Does `*-2-into` (entry 788) actually reach the `short-float` branch?

The `number-case` macro dispatches on `(typecode y)`. For a misc object, `typecode` reads the header subtag. For our single-float objects, this should return `subtag-single-float = 0x0f = 15`.

The compiled `number-case` generates a `case` statement comparing the typecode against target-specific constants. Is the single-float case value `15` (= `0x0f`) in the compiled code? Or could there be a mismatch between the cross-compiler's idea of `subtag-single-float` and the runtime's actual subtag?

Read `wasm-arch.lisp` and confirm: `subtag-single-float = (logior fulltag-immheader (ash 1 ntagbits)) = (logior 7 8) = 15 = 0x0f`. Then check `arm-constants.h`: `subtag_single_float = IMM_SUBTAG(1) = 7 | (1 << 3) = 15 = 0x0f`. These should match.

### 3. What compilation policy is active for `l0-numbers.lisp`?

When `l0-numbers.lisp` is cross-compiled by the WASM backend:
- Is `*acode-rewrite-trust-declarations*` true or false?
- Is `safety` 0 or higher?
- Does `%short-float*-2!` get compiled with `trust-declarations`?

Check the cross-compilation environment setup. Is there a global `(declare (optimize ...))` or a `*default-optimize-settings*` that enables trust-declarations?

### 4. Can you decompile entry 750 (`%SHORT-FLOAT*-2!`) to WAT?

The compiled modules are in `build/wasm32/modules/`. Entry 750 is in one of the boot modules. Extract the WASM binary for this entry and decompile it to WAT. Look for:
- `f32.mul` instruction — means inline float multiply (correct)
- `call $wasm_call_subprim_fixnum` with `i32.const 12` — means generic `*` via `.SPbuiltin-times` (recursive, broken)

### 5. Similarly, can you decompile entry 788 (`*-2-INTO`)?

Look at the `number-case` dispatch in the compiled code. Find the branch for `short-float`. What does it do? Does it call entry 750 (`%short-float*-2!`)? Or does it do something else?

### 6. Trace the actual call chain from `*-2` entry to the error

`*-2` (entry 785) calls `*-2-INTO` (entry 788). `*-2-INTO` does `number-case` dispatch. If it reaches the `short-float` branch, it calls `sfloat-rat` expansion which calls `%short-float` and `%short-float*-2!`. If `%short-float*-2!` recurses back to `*-2`, we get:

```
*-2 (785) → *-2-INTO (788) → sfloat-rat → %short-float*-2! (750) → (* x y) → *-2 (785) → ...
```

This recursion would hit the depth limit (800) and set `pending_throw = 1`. But the error we see is XWRONGTYPE, not depth overflow. So either:
- The recursion doesn't happen (declarations ARE trusted, and the bug is elsewhere)
- The recursion happens but causes a different failure mode before hitting depth 800

### 7. What does the error dump actually mean?

At error time:
```
arg_x = 0x00000274 = box_fixnum(157) = WASM_XWRONGTYPE
arg_y = 0x0ff96e5e (ft=6=fulltag_misc) — the datum with wrong type
arg_z = 0x0fb96e4d (ft=5=fulltag_cons) — the expected type specifier
```

`arg_z = 0x0fb96e4d` with `fulltag_cons = 5`. This is a CONS cell — a type specifier in cons form. What type specifier is at this address? Can you read the CAR and CDR of `0x0fb96e4d` to determine the expected type? (CAR at offset -5+0=untagged, CDR at offset -5+4=untagged+4.)

`arg_y = 0x0ff96e5e` with `fulltag_misc = 6`. What is the subtag of this object? Read its header at `0x0ff96e5e - 6 + (-2) = 0x0ff96e56` (misc-header-offset = -2). This tells us what type the "wrong" datum actually is.

### 8. Is `>-2` compiled differently from `*-2`?

`>-2` succeeds with single-floats. `*-2` fails. Both use `number-case` dispatch. The key difference:
- `>-2` for `(fixnum × short-float)` calls `(fixnum-sfloat-compare x y)` — a direct function
- `*-2` for `(fixnum × short-float)` calls `(sfloat-rat * y x)` — a macro that expands to `%short-float*-2!` which recursively calls generic `*`

If the `>-2` path never recurses through generic arithmetic, it avoids the trust-declarations issue. Check whether `fixnum-sfloat-compare` uses any generic arithmetic internally, or whether it's all primitive operations.

### 9. Anything else

The root cause appears to be one of:
1. **Untrusted declarations** → `%short-float*-2!` recurses through generic `*` → stack overflow or corruption
2. **Wrong typecode comparison** → `number-case` generates wrong constant for `short-float` → falls through to XWRONGTYPE
3. **Something in `sfloat-rat` expansion** that doesn't work on WASM 32-bit

Find which one it is, and suggest a fix.

---

## Key Files

| File | What's There |
|------|-------------|
| `level-0/l0-numbers.lisp` | `*-2` (715), `*-2-INTO` (720), `sfloat-rat` macro (50-59), `*sfloat-dops*` (33), `%short-float*-2!` (124), `>-2` (search), `fixnum-sfloat-compare` (search) |
| `level-0/l0-float.lisp` | `%short-float` (556), `%fixnum-sfloat` (699), `%int-to-sfloat!` (search) |
| `level-0/WASM/wasm-float.lisp` | WASM-specific `%int-to-sfloat!` (372), `%copy-short-float` (234) |
| `compiler/WASM/wasm2.lisp` | `wasm2-%short-float*-2` (627), `wasm2-mul2` (257), `wasm2-emit-box-single` (5132), `wasm2-typecode` (1155) |
| `compiler/WASM/wasm-arch.lisp` | `subtag-single-float` (259), `%make-sfloat` macro (834), `single-float-tag-is-subtag` (813) |
| `compiler/acode-rewrite.lisp` | `*acode-rewrite-trust-declarations*` (23), `mul2` rewrite rule (306-360) |
| `lib/number-case-macro.lisp` | `number-case` macro (93-162), WASM no-retry-loop variant (154-158) |
| `lisp-kernel/wasm-subprims-provider.c` | `wasm_call_builtin` (767), `wasm_call_function_or_symbol` (2737), depth limit (2805) |
| `build/wasm32/modules/` | Compiled WASM modules containing entries 750, 785, 788 |

---

## Specific Questions for Codex

1. Does entry 750 (`%SHORT-FLOAT*-2!`) import `wasm_call_subprim_fixnum`? If yes, it's making recursive generic arithmetic calls.

2. What compilation policy is active when `l0-numbers.lisp` is cross-compiled? Is `trust-declarations` enabled?

3. Read the CAR/CDR of `arg_z=0x0fb96e4d` (the expected type specifier cons) and the header of `arg_y=0x0ff96e5e` (the wrong-type datum). What types are involved in the XWRONGTYPE error?

4. If `%short-float*-2!` does recurse, what is the fix? Options:
   - (a) Enable `trust-declarations` for `l0-numbers.lisp` compilation
   - (b) Rewrite `%short-float*-2!` to use `%short-float*-2` (the vinsn) directly instead of generic `*`
   - (c) Add `(declare (optimize (speed 3) (safety 0)))` to `%short-float*-2!`
   - (d) Something else

5. Is the `funcall_depth > 800` limit causing silent corruption before the XWRONGTYPE surfaces?
