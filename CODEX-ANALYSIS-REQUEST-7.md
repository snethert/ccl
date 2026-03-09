# Codex Read-Only Analysis Request: `mul2` → `.SPbuiltin-times` fix applied but error persists

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

**Output: Include a suggested solution (with code samples) in your report. Do NOT apply the solution.**

**Scope: Open-ended. Tell us everything you find, including things we haven't asked about.**

---

## What Changed Since CODEX-ANALYSIS-REQUEST-6

We implemented your recommended fix from request 6. Uncommitted changes now include:

### Applied Fix: Generic arithmetic lowered to builtin subprims

In `compiler/WASM/wasm2.lisp`:
- `wasm2-mul2` (line 257) → now calls `wasm2-emit-builtin-subprim-binary-call seg xfer '.SPbuiltin-times x y`
- `wasm2-add2` (line 187) → now calls `wasm2-emit-builtin-subprim-binary-call seg xfer '.SPbuiltin-plus x y`
- `wasm2-sub2` (line 216) → now calls `wasm2-emit-builtin-subprim-binary-call seg xfer '.SPbuiltin-minus x y`

The `%i+`/`%i-`/`%i*` forms (compiler-guaranteed fixnum) remain unchanged with `:fixnum-add/sub/mul`.

### Removed diagnostic code
- Removed MV2 log in `wasm_return_values2`
- Removed MAI/MA logs in `_SPmisc_alloc_init`/`_SPmisc_alloc`
- Removed `wasm_diag_arg_x_stats` counter/export

### Build result
**The build succeeds but the error persists.** The error is subtly different now — read on.

---

## Current Build Output (Relevant Excerpt)

```
[stage] cold-boot-init starting (const-pool installs so far: 0, skipped: 0)
cold-boot-init: fn=0x0412d8be entry=0x00001168 (idx=1114)

=== STATE DUMP: ksignalerr ===
  imm0     = 0x00000000
  imm1     = 0x000000c8
  nargs    = 0x0000000c
  rctx     = 0x00000000
  arg_z    = 0x0fb96e4d
  arg_y    = 0x0ff96e5e
  arg_x    = 0x00000274
  temp0    = 0x00000000
  temp1    = 0x00000000
  nfn      = 0x04117546
  vsp      = 0x0222afd0
  Rfn      = 0x04117546
  allocptr = 0x00000000
  spill: sp=0x0224ab04 base=0x0222b700 limit=0x0224b700 depth=767
  catch_top=0x00000000 db_link=0x00000000 pending_throw=0x00000000
  VSP=0x0222afd0 top: 0x0fb96e66 0x000000f0 0x0fb96e66 0x000000f0
  spill_push=5619 spill_pop=4852
  last_cpr: e=836 s=0 val=0x0411755e
=== END STATE DUMP ===
  expected=0x0fb96e4d ft=5 (0x0411962e 0x00000080)
ksignalerr: absorbed=0x00000001 calls=0x00000001
cold-boot-init: pending_throw=0x00000040 startup-step=40
cold-boot-init: ok (infra ready, errors absorbed)
```

---

## Analysis of State Dump

### Register decode

| Register | Value | Meaning |
|----------|-------|---------|
| `arg_x` | `0x00000274 = box_fixnum(157)` | WASM_XWRONGTYPE = 157. This is a **type error**, not XARRLIMIT! |
| `arg_y` | `0x0ff96e5e` (ft=6) | Datum with wrong type. fulltag=6=`fulltag_immheader` — NOT a valid Lisp object |
| `arg_z` | `0x0fb96e4d` (ft=5) | Expected type specifier. fulltag=5=`fulltag_misc` — looks like a pointer but at ~264MB |
| `nargs` | `0x0c = 12` | 12 arguments on the stack (this is how `_SPksignalerr` was called) |
| `imm1` | `0xc8 = 200` | Unknown significance |
| `nfn` | `0x04117546` | Current function object |
| `last_cpr` | `e=836` | Last const-pool-referenced entry = 836 |
| `pending_throw` | `0x40 = box_fixnum(16)` | Set after ksignalerr absorbs |

### Vstack decode

```
VSP top: 0x0fb96e66 0x000000f0 0x0fb96e66 0x000000f0
```

- `0x000000f0 = box_fixnum(60)` = `new-size` (correct, same as before)
- `0x0fb96e66` appears twice — this is the garbage value (ft=6=`fulltag_immheader`)

### Key differences from previous build

| Aspect | Before (request 6) | After (this build) |
|--------|--------------------|--------------------|
| Error type | XARRLIMIT (count too large) | XWRONGTYPE (type mismatch) |
| Garbage value | `0x0fb96e7c` (ft=4=tag_fixnum) | `0x0fb96e4d` (ft=5=fulltag_misc) |
| Error source | `_SPmisc_alloc` overflow check | Type check somewhere in generic `*` path |
| `pending_throw` | `0x48 = box_fixnum(18)` | `0x40 = box_fixnum(16)` |

### Spill stack imbalance

```
spill_push=5619 spill_pop=4852
depth=767
```

There is a **net 767-value imbalance** between spill pushes and pops. This is very concerning. `wasm2-with-spilled-locals` spills all spillable i32 locals before a C call and restores them after. If the push/pop counts don't match, locals are being corrupted.

### Address analysis

Both `0x0fb96e4d` and `0x0ff96e5e` are at ~264MB, far beyond:
- Dynamic heap: `0x4110000–0x4378360` (~65–67MB)
- Purespace: `0x110000–0x1cecf8` (~1–29MB)
- Spill stack: `0x0222b700–0x0224b700` (~34MB)

These addresses are in the **WASM linear memory growth region** but beyond any initialized area. They look like raw bit patterns that happen to land in high memory — i.e., they are computed garbage, not valid pointers.

---

## The Problem

The `mul2` → `.SPbuiltin-times` fix changed the error from XARRLIMIT to XWRONGTYPE, which means the code path DID change — the builtin subprim IS being called. But:

1. `_SPbuiltin_times` detects non-fixnum args → falls through to `wasm_call_builtin(WASM_BUILTIN_TIMES, 2)`
2. `wasm_call_builtin` reads `%builtin-functions%[2]` to get the symbol `*-2`
3. `wasm_call_builtin` swaps arg_z ↔ arg_y (WASM→ARM convention), then calls `wasm_call_function_or_symbol` with `*-2`
4. `*-2` must be fbound. Is it? `*-2` is defined in `l0-numbers.lisp:715`. It should be compiled and installed as a module.
5. `*-2` dispatches on argument types, calls the appropriate multiply routine
6. Somewhere in this chain, a type error is raised with garbage arguments

### Hypotheses

**Hypothesis A: `*-2` is not fbound at cold-boot-init step 40.** The JS pipeline installs compiled modules before calling `cold-boot-init`, but maybe `*-2` is missing from the module bundle, or its const pool is not installed. If `*-2` is unbound, `wasm_call_function_or_symbol` would signal an error.

**Hypothesis B: The spill stack imbalance corrupts locals.** 767 unpopped spill values means that across 5619 pushes and 4852 pops, 767 values were pushed but never popped. This could mean:
- A subprim call that spills locals but early-returns (via pending_throw) without restoring them
- `wasm2-emit-builtin-subprim-binary-call` spills locals for the call, but the result-retrieval code (`:arg0` after the call) doesn't account for changed spill state
- Each unmatched push shifts the spill stack by one slot, causing all subsequent spill restores to load wrong values

**Hypothesis C: The argument values passed to `_SPbuiltin_times` are already garbage.** The garbage might originate upstream — in `(/ 1.0 0.85)` which computes `rehash-ratio`. `div2` already uses `.SPbuiltin-div` (confirmed: line 291 calls `.SPbuiltin-div`), which also falls through to `wasm_call_builtin(WASM_BUILTIN_DIV, 2)`. If the same spill corruption affects the division, `rehash-ratio` itself is garbage, and everything downstream is garbage too.

**Hypothesis D: `wasm2-emit-builtin-subprim-binary-call` has a bug in how it handles `:return-constant` + `:return`.** The function does:
```lisp
(wasm2-form seg nil nil x)       ;; evaluate x
(wasm2-form seg nil nil y)       ;; evaluate y
(wasm2-emit :set-arg1)           ;; pop y → arg_y
(wasm2-emit :set-arg0)           ;; pop x → arg_z
(wasm2-emit-call-subprim subprim) ;; call subprim (spills/restores locals)
(wasm2-emit :arg0)               ;; push result (arg_z) onto WASM stack
(when (wasm2-returning-p xfer)
  (wasm2-emit :return-constant)  ;; ???
  (wasm2-emit :return))          ;; return
```
What does `:return-constant` do? If this is wrong, the return value from the builtin call could be discarded and replaced with something else.

---

## What We Want Investigated

### 1. Is `*-2` fbound at cold-boot-init step 40?

Check the startup plan and module bundles. Find what entry index `*-2` maps to. Is it in the boot modules (`wasm-boot-modules.json`) or runtime modules? If runtime modules, those may not be installed yet at step 40.

Check: does `make-real-image.mjs` install all modules (boot + runtime) before calling `cold-boot-init`? Or does it call `cold-boot-init` first and install modules later?

### 2. Trace `wasm2-emit-builtin-subprim-binary-call` more carefully

Specifically:
- What does `:return-constant` emit in WASM? Look at the WASM emission backend for this opcode.
- Is the sequence `call-subprim → :arg0 → :return-constant → :return` correct?
- Compare with how `div2` (which was already using this function) works — does `div2` ever succeed during cold-boot?

### 3. Investigate the spill stack imbalance (push=5619, pop=4852)

This is a **767-value net imbalance**. This is very suspicious. Questions:
- Does `wasm2-emit-call-subprim` wrap the call with `wasm2-with-spilled-locals`, which does `:spill-locals` / `:restore-locals`?
- If the subprim call triggers an error and `pending_throw` is set, does the `:restore-locals` still execute? Or does the early return in `wasm_call_function_or_symbol` skip the restore?
- Trace the C code path: `_SPbuiltin_times` → `wasm_call_builtin` → `wasm_call_function_or_symbol`. If `wasm_call_function_or_symbol` returns early due to pending_throw or error, does the WASM function that called `_SPbuiltin_times` still execute the `:restore-locals` code?

### 4. Check `wasm_call_function_or_symbol` error handling

When `wasm_call_function_or_symbol` is called with a symbol (not a function), it needs to:
1. Look up the symbol's function binding
2. Call that function

If the symbol is unbound, what happens? Does it signal `error_udf`? Or does it silently return garbage?

### 5. What is entry 836?

`last_cpr: e=836` — what function is entry 836? Is it `*-2`, `+-2`, `/-2`, or something else? This tells us what was running when the error occurred.

### 6. Decode `nfn = 0x04117546`

This is in the dynamic heap range. What function does this point to? Can you decode its header to determine the entry index?

### 7. Check if `(/ 1.0 0.85)` succeeds

`make-hash-table` line 464 does:
```lisp
(setq rehash-threshold (/ 1.0 (max 0.01 rehash-threshold)))
```

This is float division, which goes through `div2` → `.SPbuiltin-div` → `wasm_call_builtin(WASM_BUILTIN_DIV, 2)` → `/-2`. If this also fails with a type error, the garbage propagates to `(* 60 rehash-ratio)`. But the error count shows `absorbed=1 calls=1` — only ONE error. So either division succeeds (unlikely if `/-2` has the same issues as `*-2`), or the first error is from the division and the multiplication never runs.

### 8. Anything else

The spill stack imbalance is deeply concerning. If every `wasm2-emit-call-subprim` spills N locals but only pops N-k of them (because of early returns or error paths), each subsequent call reads shifted values from the spill stack. This would cause cascading corruption.

---

## Key Files

| File | What's There |
|------|-------------|
| `compiler/WASM/wasm2.lisp` | `wasm2-mul2` (257), `wasm2-add2` (187), `wasm2-sub2` (216), `wasm2-div2` (289), `wasm2-emit-builtin-subprim-binary-call` (262), `wasm2-emit-call-subprim` (4950), `wasm2-with-spilled-locals` (search), `:spill-locals`/`:restore-locals` emission |
| `lisp-kernel/wasm-subprims-provider.c` | `_SPbuiltin_times` (4335), `_SPbuiltin_div` (4354), `wasm_call_builtin` (740), `wasm_builtin_function` (706), `wasm_signal_wrong_type` (682), `_SPksignalerr` |
| `lisp-kernel/wasm-kernel-stubs.c` | `wasm_call_function_or_symbol`, `wasm_spill_push`/`wasm_spill_pop`, `wasm_return_values2` |
| `level-0/l0-numbers.lisp` | `*-2` (715), `/-2` (828), `+-2` (510) |
| `level-0/l0-hash.lisp` | `make-hash-table` (431), `compute-hash-size` (516) |
| `level-0/nfasload.lisp` | `%run-cold-boot-init` (1268), step 40 (1285) |
| `xdump/xfasload.lisp` | `%builtin-functions%` vector definition (325) |
| `scripts/wasm/lib/make-real-image.mjs` | Build pipeline, module install order, cold-boot-init invocation |

---

## Git Context

```
Branch: wasm-port
HEAD: 8317da5f wasm: defer runtime const-pool install to after cold-boot-init

Uncommitted changes (9 files):
 M compiler/WASM/wasm2.lisp              (mul2/add2/sub2 → builtin subprims)
 M lisp-kernel/pmcl-kernel.c             (advance C heap past purespace)
 M lisp-kernel/wasm-kernel-stubs.c       (funcall_common pending_throw fix, diagnostic cleanup)
 M lisp-kernel/wasm-no-wasi-libc.c       (wasm_advance_malloc_past)
 M lisp-kernel/wasm-subprims-provider.c  (wasm_nil() cache, pending_throw guards, diagnostic cleanup)
 M lisp-kernel/wasm32/subprims/Makefile  (--global-base=10485760, diagnostic export removed)
 M scripts/wasm/lib/load-image.mjs       (wasm_set_subprims_nil call)
 M scripts/wasm/lib/make-real-image.mjs  (wasm_set_subprims_nil, installConstPools: true)
 M scripts/wasm/rebuild-everything.sh    (subprims layout gap validation)
```
