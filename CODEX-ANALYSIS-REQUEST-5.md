# Codex Read-Only Analysis Request: cold-boot-init pending_throw=0x48 at startup-step=0

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

**Scope: Open-ended. Tell us everything you find, including things we haven't asked about.**

---

## What Changed Since CODEX-ANALYSIS-REQUEST-4

We implemented the plan from request 4 and added a second commit to phase const pool installation. Two new commits:

```
8317da5f wasm: defer runtime const-pool install to after cold-boot-init
0cb898c9 wasm: eliminate const pool bloat — emit class-refs, pre-bake pools, simplify launch
```

### Commit 0cb898c9 — Const pool bloat elimination
- Serializer emits class-ref (tag 18, ~30 bytes) instead of gvector deep-copy (tag 5, ~2.2 MB) for named class objects
- Tag 18 handler wraps interned symbol in sentinel cons `(symbol . fixnum-0x434C)`
- New `wasm_const_pool_resolve_class_refs` export resolves sentinels via FIND-CLASS after cold-boot-init
- Spill push/pop fail-fast on NULL instead of silent nil return
- `wasm_const_pool_ref` slow path traps instead of calling host callback
- Launcher simplified: no on-demand install, no scratch memory, no repair pass
- modules.bin stripped of const pool data (code only)

### Commit 8317da5f — Phased const pool install
- Runtime modules install with `installConstPools: false` — code only, no pools
- Boot modules keep `installConstPools: true` — 621 boot pools installed during module install
- New Phase 2C pass installs ~5,500 runtime pools AFTER cold-boot-init + FASL loading + RESTORE-LISP-POINTERS
- Phase-aware synthesis guard in `wasm_intern_startup`:
  - STARTUP phase (boot pool install): synthesis allowed as fallback
  - RUNTIME phase (late pool install): synthesis blocked, return 0 → tag handler stores NIL/UDF placeholder
- Class-ref resolver hardened: checks `subtag_symbol` on car of sentinel cons
- Cold-boot diagnostic: scans for duplicate `*WASM-STARTUP-STEP*` symbols when step=0

---

## Current Build Output

```
[stage] compiled modules: 7558/7560 installed, 0 failed, 2 skipped (boot)
[stage] image fixup: 1019 in-place + 5 new-alloc / 1111 total (10796 syms, 0 skipped, 87 unmatched)
[stage] filled 121 null table slots with trap stub
[stage] cold-boot-init starting (const-pool installs so far: 0, skipped: 0)
[stage] pre-cold-boot heap profile:
HEAP-PROFILE: total=3473408 (3 MiB) cons=53551 (0 MiB)
  0xfa svec n=1823 b=2656192 (2 MiB)
  0x3a sym n=5363 b=171616 (0 MiB)
  0x2a func n=6756 b=161920 (0 MiB)
  0xbf string n=177 b=20848 (0 MiB)
  0x82 istruct n=119 b=6632 (0 MiB)

cold-boot-init: fn=0x0412d8be entry=0x00001168 (idx=1114)
cold-boot-init: pending_throw=0x00000048 startup-step=0
cold-boot-init: threw (infra incomplete)
FAIL: wasm_run_cold_boot_init returned -6
```

Build never reaches the late pool install (Phase 2C), class-ref resolution, or image save because cold-boot-init fails.

---

## The Problem

`cold-boot-init` fails with `pending_throw=0x48` at `startup-step=0`.

- `0x48` as fixnum = 18. We could not identify what error code 18 represents. It is NOT the `_SPksignalerr` absorbed error code (that's fixnum 16 = 0x40).
- `startup-step=0` means the throw happened BEFORE the first line of `%RUN-COLD-BOOT-INIT` body executed — before `(%wasm-note-startup-step 10)` at line 1277.
- The new duplicate-symbol diagnostic did NOT fire, meaning there is no synthesized `*WASM-STARTUP-STEP*` masking the canonical one.
- Entry 1114 is `%RUN-COLD-BOOT-INIT`. It is a boot module entry. Its const pool should be installed (boot modules use `installConstPools: true`).

### What we ruled out

| Hypothesis | Evidence |
|-----------|----------|
| Runtime pools corrupt cold-boot-init | Same error with runtime pools installed (186 MiB heap) AND without (3 MiB heap) |
| Symbol synthesis creates bad symbols | Same error with synthesis enabled AND disabled |
| Class-ref sentinel cons cells cause TYPE-ERROR | Same error before class-ref fix existed |
| Duplicate `*WASM-STARTUP-STEP*` masks progress | Diagnostic scan found no duplicates |
| GC corruption | `new_heap_segment` doesn't trigger GC; no GC runs before cold-boot-init |

### What we suspect but cannot confirm

Our memory notes from earlier sessions say: "Adding static arrays (e.g., `uint32_t[20]`) to `wasm-kernel-stubs.c` causes `startup-step=0 pending_throw=0x48` failure. Likely WASM linker data layout sensitivity."

We added several statics in recent commits:
- `wasm_heap_profile`: `static const char *subtag_names[256]`, `static int names_init`
- Entry-fn cache: `static LispObj *wasm_entry_fn_cache`, `static uint32_t wasm_entry_fn_cache_size` (+ hits/misses)
- `wasm_cpr_fail_count`: `static uint32_t`
- Various `static const uint8_t[]` string literals in new functions

The WASM linker places C statics in the linear memory data section. If the data section grows, it could:
1. Shift the initial stack pointer or heap base
2. Overlap with the area where the boot image expects nil/symbols to be
3. Change `__data_end` / `__heap_base` which the kernel uses for heap layout

---

## What We Want

1. **Trace the FUNCALL into `%RUN-COLD-BOOT-INIT`.** The C code at `wasm_run_cold_boot_init` (line 3873-3881 in wasm-kernel-stubs.c) calls `wasm_call_subprim_fixnum(wasm_subprim_fixnum(WASM_SUBPRIM_FUNCALL_INDEX))` with `nfn=fn` and `nargs=0`. What does the FUNCALL subprim do? Does it access the function's const pool? What exactly triggers the pending_throw=0x48?

2. **Identify error code 0x48.** `pending_throw` stores a raw LispObj. 0x48 = fixnum 18. What does 18 mean in CCL's error/condition system? Trace how `_SPksignalerr` or other error-signaling subprims set `wasm_pending_throw`. Is 18 a type-error code, an undefined-function code, or something else?

3. **Investigate WASM data layout sensitivity.** Read the linker flags in `lisp-kernel/wasm32/Makefile`, check `--stack-first`, `--initial-memory`, `--global-base`, `--table-base` etc. Compare with what the boot image expects (blobBase, nilreg, heap areas). Could adding ~2 KB of static data shift something critical?

4. **Check entry 1114's const pool.** Is it installed? Does `nrs_WASM_CONST_POOLS.vcell[1114]` contain a valid simple-vector? If so, are its slots valid? If `%RUN-COLD-BOOT-INIT` loads a const pool ref in its prologue (before any user-visible code), what slot does it access and what value does it get?

5. **Anything else.** Read the code freely and report what you find.

---

## Key Files

| File | What's There |
|------|-------------|
| `lisp-kernel/wasm-kernel-stubs.c` | `wasm_run_cold_boot_init` (line 3808), `wasm_intern_startup` (line 5806), synthesis guard (line 5834), `wasm_const_pool_install_inner` tag handlers (line 6146+), `wasm_const_pool_resolve_class_refs` (line 6762), `wasm_const_pool_ref` (line 6848), spill push/pop (line 2150), heap profiler (line 584) |
| `lisp-kernel/wasm32/Makefile` | WASM linker flags, `--table-base=256`, exports |
| `lisp-kernel/pmcl-kernel.c` | `lisp_nil` initialization, `reclaimable_area` setup |
| `lisp-kernel/image.c` | `load_image` — how boot image maps into memory |
| `level-0/nfasload.lisp` | `%run-cold-boot-init` (line 1268), `*wasm-startup-step*` (line 1254) |
| `compiler/WASM/wasm2.lisp` | Compiler output — how function prologues access const pools |
| `scripts/wasm/lib/make-real-image.mjs` | Build pipeline — module install, cold-boot-init call, Phase 2C late pool install |

---

## Git Context

```
Branch: wasm-port
HEAD: 8317da5f wasm: defer runtime const-pool install to after cold-boot-init

Recent commits:
8317da5f wasm: defer runtime const-pool install to after cold-boot-init
0cb898c9 wasm: eliminate const pool bloat — emit class-refs, pre-bake pools, simplify launch
40af098c wasm: skip invariant fcell gate (O(N) heap scan per symbol is too slow)
419a71e1 wasm: skip Lisp save path when const pools are partial
bda1d865 wasm: skip proactive const-pool install, defer to launch time
a6144e84 wasm: add post-module-install GC to compact heap before restore-lisp-pointers
d7e54001 wasm: add pre-save GC to wasm_save_image_direct
553ded6a wasm: fix function-table collision — add --table-base=256 to linker
```
