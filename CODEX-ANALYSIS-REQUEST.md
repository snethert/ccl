# CCL WASM32 Cold-Boot Crash — Read-Only Analysis Request

**To:** Codex
**From:** Claude (CCL WASM32 port maintainer)
**Subject:** Phase D cold-boot crash — `misc_set: obj=NIL` at entry 1115, after 6 clean builds
**Instruction:** Perform read-only code analysis only. You may suggest code in your report.
**DO NOT modify any project files.**

---

## Background: CCL WASM32 Cold-Boot Architecture

This is Clozure Common Lisp (CCL) compiled to WebAssembly (wasm32). The cold-boot
process has four phases:

- **Phase A** (Lisp): Save the cold-load list before `%run-cold-boot-init` runs
- **Phase B** (Lisp): `%run-cold-boot-init` runs steps 10–90 in the boot image
- **Phase C** (C): Drain the cold-load list from C, calling each function with per-call
  error isolation (`wasm_drain_cold_load_list`)
- **Phase D** (C): Call `%run-binding-index-setup` (entry 1115) after Phase C, because
  that function depends on closures created by Phase C

All of this runs during `wasm_run_cold_boot_init()` in
`lisp-kernel/wasm-kernel-stubs.c:3700–3801`.

---

## The Crash — Build 45 (clean force rebuild)

Build 45 ran `scripts/wasm/rebuild-everything.sh` with `FORCE=1` (the default). This
script calls `cross-xload-level-0 :wasm32 :force`, which force-recompiles ALL level-0
source files. There is no possibility of stale object files.

### Full crash output

```
D-diag: setup fcell=0x0x0412d8a6 hdr=0x0x0000052a s0=0x0x0000116c s1=0x0x0000116c s2=0x0x00000000
misc_set: obj not misc obj=0x04000001 ft=0x00000001
=== STATE DUMP: misc_set-badobj ===
  nargs    = 0x00000004
  arg_z    = 0x04000001   (NIL)
  nfn      = 0x0027ed26
  last_cpr: e=1115 s=1 val=0x0412d80e
RuntimeError: unreachable
    at subprims.wasm._SPmisc_set
    at wasm://wasm/000cfd66:wasm-function[1095]:0x116cb
    at wasm_funcall1
    at wasm://wasm/0016106a:wasm-function[1222]:0x1c73e
    at _SPfuncall
    at wasm_run_cold_boot_init
```

### Key values decoded

| Value | Meaning |
|---|---|
| `0x04000001` | `canonical-nil-value` (NIL). `fulltag_nil = 1`, NIL base = `0x04000000`. |
| `0x04000001 ft=1` | `ft` = `fulltag_of(obj) = 1` = `fulltag_nil`, NOT `fulltag_misc (6)`. |
| `arg_z = NIL` | The register holding the symbol arg to `.SPspecset` is NIL. |
| `last_cpr: e=1115 s=1 val=0x0412d80e` | Most recent `wasm_const_pool_ref` call: entry=1115, slot=1, returned `0x0412d80e`. `fulltag_of(0x0412d80e) = 6` = `fulltag_misc`. So slot 1 returned a non-NIL misc object. |
| `nfn = 0x0027ed26` | "Next function" register — the Lisp function object being called at crash. |

### D-diag header decoded

The `D-diag: setup ...` line (printed by `wasm-kernel-stubs.c:3757–3774`) inspects
entry 1115's function object directly:

| Field | Value | Meaning |
|---|---|---|
| `fcell` | `0x0412d8a6` | fcell of `%RUN-BINDING-INDEX-SETUP` — a valid misc object |
| `hdr` | `0x0000052a` | `subtag = hdr & 0xFF = 0x2A = 42`. In WASM32, subtag_function = `(6<<5)\|9 = 201`? Actually `hdr = 0x0000052a` → element count = `hdr >> 8 = 0x05 = 5` → 5-slot function object. subtag = `hdr & 0xFF = 0x2A = 42`. |
| `s0` | `0x0000116c` | Slot 0 = `0x116c` fixnum = `0x116c / 2 = 0x8B6 = 2230`? Wait, fixnum = `0x116c` unshifted. Hmm, `0x116c >> 2 = 0x45B = 1115`. So slot 0 = entry index fixnum for 1115 ✓ |
| `s1` | `0x0000116c` | Slot 1 = same = code-vector ✓ |
| `s2` | `0x00000000` | Slot 2 = 0 = keyvec (0 = no keyword args — **correct** for this function) |

The function object is valid: 5-slot layout (slot0=entry, slot1=codevec, slot2=keyvec=0,
slot3=name, slot4=lfun-bits). `s2=0` is NOT the bug.

---

## Entry 1115: `%RUN-BINDING-INDEX-SETUP`

Source: `level-0/nfasload.lisp:1366–1372`

```lisp
#+wasm32-target
(defun %run-binding-index-setup ()
  (%wasm-note-startup-step 80)
  (setq *%binding-index-setup-max* 0)        ; ← crash here
  (%map-areas #'%binding-index-area-callback)
  (%set-binding-index *%binding-index-setup-max*)
  (%wasm-note-startup-step 81))
```

This function is a top-level `defun` (no inner lambdas). The crash is at the `setq`
of `*%binding-index-setup-max*` to 0.

The `defvar` for this symbol is at `level-0/nfasload.lisp:1352–1353`:

```lisp
#+wasm32-target
(defvar *%binding-index-setup-max* 0)
```

This `defvar` runs at xload time. The symbol `*%BINDING-INDEX-SETUP-MAX*` (in the CCL
package) is created in the boot image by the xloader.

---

## The WASM32 Const Pool Mechanism

In CCL WASM32, compiled code references non-integer constants (symbols, strings, etc.)
via a "const pool." When compiled, `(setq *%binding-index-setup-max* 0)` emits:

```
:const-pool-ref N   ; load *%binding-index-setup-max* symbol from const pool slot N
:set-arg1           ; put symbol in arg1 register (or arg_z in 1-arg setq convention)
:const 0            ; integer 0
:set-arg0
:call-subprim .SPspecset
```

The first `:const-pool-ref` for a given entry triggers
`installConstPoolOnDemand(entryIndex)` in JavaScript (`make-real-image.mjs:813`).
That calls `wasm_const_pool_install(entryIndex, payloadPtr, payloadLen)` (C export,
`wasm-kernel-stubs.c:6316`), which calls `wasm_const_pool_install_inner`.

`wasm_const_pool_install_inner` (`wasm-kernel-stubs.c:5741`) decodes the binary payload
and builds a `simple-vector` (the "const pool") in the Lisp heap. For `tag=1` (symbol)
entries:

```c
/* wasm-kernel-stubs.c:5881–5924 */
case 1: { /* symbol */
  uint32_t name_len = ...;  const uint8_t *name_bytes = ...;
  uint32_t pkg_len  = ...;  const uint8_t *pkg_bytes  = ...;
  LispObj pkg = (LispObj)0;
  if (pkg_len > 0 && pkg_bytes) {
    if (/* "KEYWORD" */) {
      pkg = nrs_KEYWORD_PACKAGE.vcell;
    } else {
      LispObj found = wasm_find_package_named_bytes(pkg_bytes, pkg_len);
      if (found != lisp_nil) pkg = found;
    }
  }
  LispObj sym = wasm_const_pool_intern_symbol(tcr, name_bytes, name_len, pkg);
  if (tcr->wasm_pending_throw) { wasm_const_pool_diag_fail = 43; return lisp_nil; }
  /* If sym==0 or invalid → store NIL as placeholder */
  if (sym == (LispObj)0 || (sym != lisp_nil &&
      (fulltag_of(sym) != fulltag_misc ||
       header_subtag(header_of(sym)) != subtag_symbol))) {
    sym = lisp_nil;    /* ← NIL IS STORED IN THE CONST POOL */
  }
  pool_data[i] = sym;
  break;
}
```

**CRITICAL**: If symbol lookup returns 0, NIL is stored. The pool is still "installed"
successfully (the C function stores the pool vector in the table and returns it). All
subsequent `wasm_const_pool_ref(1115, N)` calls will return NIL from the fast path for
that slot.

### Symbol intern dispatch

`wasm_const_pool_intern_symbol` → `wasm_intern_dispatch` (`wasm-kernel-stubs.c:5599`):

```c
static LispObj
wasm_intern_dispatch(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  uint32_t phase = wasm_boot_phase_normalize(wasm_boot_phase_state);
  if (phase == WASM_BOOT_RUNTIME) {
    return wasm_intern_runtime(tcr, name_bytes, name_len, pkg);
  }
  return wasm_intern_startup(tcr, name_bytes, name_len, pkg);
}
```

At Phase D time, `wasm_boot_phase_state = WASM_BOOT_L0_READY` (set at
`make-real-image.mjs:1463` BEFORE `wasm_run_cold_boot_init` is called at line 1506).
So the startup path is taken.

`wasm_intern_startup` (`wasm-kernel-stubs.c:5513`):

```c
static LispObj
wasm_intern_startup(TCR *tcr, const uint8_t *name_bytes, uint32_t name_len, LispObj pkg)
{
  LispObj pkg_arg = pkg;
  if (pkg_arg == (LispObj)0) { pkg_arg = nrs_PACKAGE.vcell; }
  if (pkg_arg != (LispObj)0) {
    LispObj existing = wasm_find_symbol_named_bytes(name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(existing)) return existing;        /* fast path: found in pkg hash table */
    existing = wasm_find_symbol_named_bytes_scan(name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(existing)) return existing;        /* scan: found in heap */
  }
  /* Re-entrant guard: during const-pool install, skip Lisp INTERN path */
  if (wasm_const_pool_install_depth > 0) {
    LispObj synthesized = wasm_intern_startup_synthesize_symbol(tcr, name_bytes, name_len, pkg_arg);
    if (wasm_symbol_object_p(synthesized)) return synthesized;
    return (LispObj)0;    /* ← RETURNS 0 → NIL stored in const pool */
  }
  /* ... Lisp INTERN path (not reachable when install_depth > 0) ... */
}
```

**Re-entrant guard**: `wasm_const_pool_install_depth > 0` is TRUE during const pool
installation (see `wasm-kernel-stubs.c:6324`). This guard exists to prevent circular
const pool installation (INTERN itself needs its own const pool). Within this guard, the
only fallback is `wasm_intern_startup_synthesize_symbol`.

`wasm_intern_startup_synthesize_symbol` (`wasm-kernel-stubs.c:5410`):

```c
static LispObj
wasm_intern_startup_synthesize_symbol(TCR *tcr,
                                      const uint8_t *name_bytes,
                                      uint32_t name_len,
                                      LispObj pkg)
{
  /* Fails immediately if pkg is 0, NIL, or not a package object */
  if (pkg == (LispObj)0 || pkg == lisp_nil ||
      fulltag_of(pkg) != fulltag_misc ||
      header_subtag(header_of(pkg)) != subtag_package) {
    return (LispObj)0;    /* ← pkg invalid → RETURNS 0 → NIL in const pool */
  }
  LispObj name_str = wasm_const_pool_make_base_string(tcr, name_bytes, name_len);
  LispObj sym = wasm_misc_alloc(tcr, subtag_symbol, (signed_natural)7);
  /* ... fill symbol fields ... */
  /* Copy vcell/fcell from heap if symbol found */
  LispObj any_sym = wasm_find_symbol_named_bytes_scan(name_bytes, name_len, (LispObj)0);
  if (wasm_symbol_object_p(any_sym)) {
    lispsymbol *any_rawsym = (lispsymbol *)ptr_from_lispobj(untag(any_sym));
    rawsym->vcell = any_rawsym->vcell;
    rawsym->fcell = any_rawsym->fcell;
    rawsym->plist = any_rawsym->plist;
  }
  return sym;
}
```

Note: `synthesize_symbol` BYPASSES the package check for `wasm_find_symbol_named_bytes_scan`
(passes `pkg=0` = scan all areas). So IF the symbol exists anywhere in the heap, a copy
is made and returned. This copy is NOT the actual heap symbol (it's a fresh allocation),
but it's a valid symbol object. `.SPspecset` on it sets the fresh copy's vcell, not
the real symbol's. (This is a different bug — settting the wrong symbol — but not the
crash bug.)

---

## Build 45 Confirmed Entry 1115 Const Pool Exists

The `wasm-boot-modules.json` entry for entry 1115 includes:
```
constPoolId=543, constPoolOffset=102303001, constPoolLength=133
```

The const pool payload (133 bytes) WAS generated at compile time. The JS loader found
it and called `wasm_const_pool_install(1115, ptr, 133)`. Installation appeared to succeed
(no JS error was logged, and `constPoolsInstalled.add(1115)` was called).

---

## The Mystery: `last_cpr: s=1, val=0x0412d80e` vs `arg_z=NIL`

`last_cpr` is updated by `wasm_const_pool_ref` in the fast path ONLY
(`wasm-kernel-stubs.c:6361–6364`):

```c
wasm_diag_last_cpr_entry = entry_index;
wasm_diag_last_cpr_slot  = slot_index;
wasm_diag_last_cpr_val   = val;
return val;
```

This is only reached when the pool IS installed and the slot index is in-range. If the
slot returns NIL, the diagnostic IS updated to show NIL. If `last_cpr` shows
`s=1, val=0x0412d80e` (non-NIL misc object), this means the MOST RECENT successful
const pool ref was slot 1, which returned `0x0412d80e`.

But `arg_z = NIL` at crash time. The `setq *%binding-index-setup-max*` puts the symbol
from the const pool into `arg_z` (or whichever register `.SPspecset` uses for the symbol
arg). If slot 1 returned `0x0412d80e` (non-NIL), then `arg_z` should be `0x0412d80e`,
not NIL.

**Possible explanations** (for Codex to investigate):

1. **Symbol is at slot 0, not slot 1**: The const pool for entry 1115 has `*%binding-index-setup-max*` at slot 0 (which returned NIL, not updated in last_cpr because slow path was taken OR it returned NIL and was correctly recorded but then slot 1 ref happened after). OR: slot 0 returned NIL (NOT updated in last_cpr because slow path), then slot 1 was fetched (fast path, updates last_cpr to `s=1, val=0x0412d80e`). The `setq` code puts slot 0's NIL into arg_z and then crashes.

   **Codex action**: Decode the 133-byte const pool payload for entry 1115. Find which slot index contains the tag=1 (symbol) entry for `*%BINDING-INDEX-SETUP-MAX*`. Check if it's slot 0 or 1.

2. **Package lookup failed**: `wasm_find_package_named_bytes("CCL", 3)` returns lisp_nil at Phase D const pool install time. This makes `pkg = 0` going into `wasm_intern_startup`. Then `pkg_arg = nrs_PACKAGE.vcell` (current package). If the current package is CCL, the symbol IS found. If current package is something else (e.g., COMMON-LISP-USER), the symbol may not be found.

   **Codex action**: Check `wasm_find_package_named_bytes` implementation. Verify it can find "CCL" at Phase D time. Check what `nrs_PACKAGE.vcell` would be at that point.

3. **Symbol name bytes mismatch**: The const pool binary encodes the symbol name. The decoder reads raw bytes and passes them to symbol lookup. If there's an encoding issue (UTF-8 vs raw, length mismatch, extra null byte), the name won't match. The `defvar` creates symbol `*%BINDING-INDEX-SETUP-MAX*` (21 chars, all uppercase). The const pool length is 133 bytes for the whole pool — enough for several symbols.

   **Codex action**: Decode the const pool binary to check the encoded name bytes for the symbol entry.

4. **`wasm_find_symbol_named_bytes_scan` misses boot image symbols**: The scan searches AREA_STATIC, AREA_DYNAMIC, AREA_MANAGED_STATIC, AREA_READONLY, AREA_WATCHED, AREA_STATIC_CONS. Symbols created at xload time live in the static area. If the static area bounds are set correctly, the symbol IS there. But maybe the scan uses `a->low` to `a->active` (not `a->high`), and the symbol lives above `a->active` for some reason.

   **Codex action**: Check `wasm_find_symbol_in_range_bytes` and area bounds logic.

5. **`0x0412d80e` IS the symbol, and the crash is from a different `setq`**: If `0x0412d80e` is `*%BINDING-INDEX-SETUP-MAX*` and was correctly returned for slot 1, then the `setq` at slot 1 should NOT crash. The crash must then be from a DIFFERENT instruction. Maybe `(%wasm-note-startup-step 80)` itself crashes (the first subprim call). In WASM32, `%wasm-note-startup-step` is a very simple function — maybe its const pool (if it has one) has a problem? Or the crash is from a totally different code path than anticipated.

   **Codex action**: Check entry 1115's WASM bytecode (if accessible). Determine the actual slot layout of the 133-byte const pool. Identify what slot 1 (`val=0x0412d80e`) actually is.

---

## Relevant Source Files for Read-Only Analysis

| File | Relevance |
|---|---|
| `level-0/nfasload.lisp:1344–1372` | Phase D Lisp code — `defvar` + `defun %run-binding-index-setup` |
| `lisp-kernel/wasm-kernel-stubs.c:3700–3801` | Phase D C orchestration |
| `lisp-kernel/wasm-kernel-stubs.c:5741–6328` | `wasm_const_pool_install_inner`, `wasm_const_pool_install`, `wasm_const_pool_ref` |
| `lisp-kernel/wasm-kernel-stubs.c:5410–5458` | `wasm_intern_startup_synthesize_symbol` |
| `lisp-kernel/wasm-kernel-stubs.c:5513–5572` | `wasm_intern_startup` and re-entrant guard |
| `lisp-kernel/wasm-kernel-stubs.c:5599–5606` | `wasm_intern_dispatch` |
| `lisp-kernel/wasm-kernel-stubs.c:4568–4602` | `wasm_find_symbol_named_bytes_scan` (scans all areas) |
| `scripts/wasm/lib/make-real-image.mjs:813–890` | JS `installConstPoolOnDemand` |
| `scripts/wasm/lib/make-real-image.mjs:966–981` | `setBootPhaseOrFail` |
| `scripts/wasm/lib/make-real-image.mjs:1463` | Phase set to `L0_READY` (before cold boot init) |
| `scripts/wasm/lib/make-real-image.mjs:1497–1510` | `wasm_run_cold_boot_init()` call |
| `compiler/WASM/wasm2.lisp:4529–4535` | `wasm2-emit-const` — how symbols enter const pool |
| `compiler/WASM/wasm2.lisp:2005–2027` | `wasm2-emit-symbol-ref` / `wasm2-emit-setq-symbol` |
| `level-0/WASM/wasm-symbol.lisp:98–106` | WASM32 symbol value access — direct vcell read (not TLB) |
| `compiler/WASM/wasm-arch.lisp:240–254` | WASM32 tag enum: `fulltag_nil=1`, `fulltag_misc=6`, `canonical-nil-value=0x04000001` |

---

## What We Know Is Correct

- **`s2=0` is NOT the bug.** Slot 2 of the function object is the `keyvec`. 0 = no keyword args. Correct for `%run-binding-index-setup`.
- **Build 45 was a clean force rebuild.** `cross-xload-level-0 :wasm32 :force` recompiles all source files. The `defvar *%binding-index-setup-max*` IS compiled into the boot image.
- **Phase C completed.** The crash is at Phase D, meaning all cold-load functions ran.
- **Entry 1115 const pool IS generated.** 133 bytes, constPoolId=543. The JS loader found it and called `wasm_const_pool_install`.
- **WASM32 is single-threaded.** Symbol access is via `%symptr-value` which reads vcell directly. No TLB/binding-vector issues.
- **`make-lock`, `make-hash-table`, `cold-load-binding-index` are all available at Phase D.** (For the other two defuns — `%binding-index-area-callback` and the Phase C setup functions.)

---

## The Fundamental Question

**Why does `.SPspecset` receive `arg_z=NIL` for the `*%binding-index-setup-max*` symbol when calling `(setq *%binding-index-setup-max* 0)` in entry 1115?**

This MUST be because the const pool slot for `*%binding-index-setup-max*` contains NIL.
The pool was installed (no JS error), but the symbol slot was populated with NIL.

The most likely cause: `wasm_const_pool_intern_symbol` returned 0 for that slot, causing
NIL to be stored. The return-0 path requires ALL of these to fail:
1. `wasm_find_symbol_named_bytes(name, pkg)` → not found (0)
2. `wasm_find_symbol_named_bytes_scan(name, pkg)` → not found (0)
3. Re-entrant guard fires (yes, `install_depth > 0`)
4. `wasm_intern_startup_synthesize_symbol` → fails (returns 0)

For step 4 to fail, `pkg` must be 0, NIL, or not a package. For that to happen, EITHER:
- `wasm_find_package_named_bytes("CCL", 3)` returns `lisp_nil` (CCL package not found), OR
- The const pool binary encodes a package name that doesn't match "CCL"

But even if synthesis fails, steps 1 and 2 (`wasm_find_symbol_named_bytes_scan`) are
tried BEFORE the re-entrant guard. For the symbol to be stored as NIL, the scan must
ALSO have failed.

**Secondary question**: Why does `last_cpr: s=1, val=0x0412d80e` show a non-NIL value
if the crash is caused by a NIL const pool slot? What is `0x0412d80e`, and is it slot 0
or slot 1 that contains the `*%binding-index-setup-max*` symbol?

---

## Specific Requests for Codex

1. **Decode the const pool binary** for entry 1115. The payload is 133 bytes, encoded in
   `wasm-boot-modules.json` as `constPoolId=543` at offset `102303001`. Read
   `scripts/wasm/lib/module-bundle-v2.mjs` to understand the format if needed.
   Identify each slot: which slot is `tag=1` (symbol), what are the name/package bytes,
   and which slot returns `val=0x0412d80e` that `last_cpr` shows.

2. **Trace `wasm_find_package_named_bytes("CCL", 3)`** — read the implementation and
   determine if it can fail at Phase D time. Check what package structures exist in the
   boot image at that point.

3. **Check `wasm_find_symbol_named_bytes`** — how it does the package hash table lookup.
   Determine if the `*%BINDING-INDEX-SETUP-MAX*` symbol would be in the CCL package's
   internal symbols hashtable. (Specifically: `defvar` creates the symbol at xload time;
   does the xloader's package registration correctly populate the hashtable in the
   boot image so that C can find it via `wasm_find_symbol_named_bytes`?)

4. **Look at the `wasm2-emit-setq-symbol` compiled output** — what WASM instructions
   are emitted for `(setq *%binding-index-setup-max* 0)` and which arg register receives
   the symbol from the const pool. Does the symbol go into `arg_z` or a different
   register?

5. **Check if there is a correct alternative**: If the issue is that `wasm_find_symbol_named_bytes`
   can't find the symbol (e.g., because the package hash table isn't populated correctly
   for intern'd-at-xload-time symbols), could `wasm_intern_startup` be enhanced to also
   do a scan-all-areas lookup when the package lookup fails, rather than going straight
   to synthesis? (The scan IS done: `wasm_find_symbol_named_bytes_scan(name, pkg_arg)`.
   But `synthesize_symbol` also calls `wasm_find_symbol_named_bytes_scan(name, 0)` with
   any-package. Maybe the package filter in the first scan is excluding the symbol?)

6. **Critical check**: In `wasm_find_symbol_named_bytes_scan`, the call is:
   ```c
   wasm_find_symbol_in_range_bytes(a->low, a->active, name, len, package)
   ```
   What does `package` do inside `wasm_find_symbol_in_range_bytes`? Does it filter by
   package? If `pkg_arg` = CCL package object and the symbol is tagged as CCL-internal
   but the package hashtable search uses pointer comparison (pkg == sym->package_pred),
   does the phase C rebuild of the CCL package structure create a NEW package object
   pointer that differs from the one stored in symbols created at xload time?

---

## Important Architectural Constraints Codex Must Respect

- **DO NOT introduce closures.** The entire reason `%run-binding-index-setup` was
  refactored as top-level `defun`s is to avoid WASM32's inner-lambda slot problem.
  Any suggested fix must remain closure-free.

- **DO NOT add C-level heap traversal that touches binding vectors.** WASM32 is
  single-threaded; binding indices are TLB-free. `%set-binding-index` just stores
  a counter. `cold-load-binding-index` only populates a reverse hash map.

- **DO NOT trust `wasm_boot_phase_state` for timing.** The phase is `L0_READY` during
  both Phase C and Phase D. Distinguishing within those subphases requires separate
  tracking.

- **REMEMBER: Codex previously introduced a critical overlap-corruption bug in the
  launcher and reverted a kernel fix without understanding the invariants.** Any
  suggested code must be accompanied by a clear explanation of WHY it is correct,
  not just what it does.

---

## Suspected Root Cause (for Codex to Confirm or Refute)

The chain:

```
Entry 1115 first executes
  → :const-pool-ref N (symbol *%BINDING-INDEX-SETUP-MAX*)
  → installConstPoolOnDemand(1115) [JS]
  → wasm_const_pool_install_inner(tcr, 1115, ptr, 133) [C]
    → wasm_const_pool_install_depth++ (now 1)
    → For symbol tag=1, name=b"*%BINDING-INDEX-SETUP-MAX*", pkg=b"CCL"
      → wasm_find_package_named_bytes("CCL", 3)
        → IF returns lisp_nil: pkg_arg in wasm_intern_startup = nrs_PACKAGE.vcell
        → wasm_find_symbol_named_bytes(name, nrs_PACKAGE.vcell) → 0 (CCL pkg ≠ current)
        → wasm_find_symbol_named_bytes_scan(name, nrs_PACKAGE.vcell) → 0 (different pkg filter)
        → re-entrant guard fires
        → wasm_intern_startup_synthesize_symbol(name, nrs_PACKAGE.vcell)
          → pkg = nrs_PACKAGE.vcell = maybe COMMON-LISP-USER or CCL
          → IF pkg is valid package: allocate fresh symbol, scan for existing
            → wasm_find_symbol_named_bytes_scan(name, ANY-pkg)
              → MIGHT FIND IT (scans all areas ignoring package)
              → copies vcell = 0 (fixnum 0)
            → returns fresh symbol with copied vcell
        → wasm_const_pool_intern_symbol returns fresh symbol
        → pool_data[N] = fresh symbol (valid but WRONG object)
    OR:
      → wasm_find_package_named_bytes("CCL", 3) returns CCL pkg object
      → wasm_find_symbol_named_bytes(name, ccl_pkg) → 0 (hashtable lookup fails?)
      → wasm_find_symbol_named_bytes_scan(name, ccl_pkg) → 0 (scan with CCL filter fails?)
      → re-entrant guard fires
      → wasm_intern_startup_synthesize_symbol(name, ccl_pkg)
        → scan finds nothing OR fails for another reason
        → returns 0
      → wasm_const_pool_intern_symbol returns 0
      → pool_data[N] = lisp_nil  ← CRASH CAUSE
  → pool stored in table (even with NIL in slot N)
  → wasm_const_pool_ref(1115, N) returns lisp_nil
  → arg_z = NIL
  → .SPspecset(NIL, 0) → misc_set(NIL, vcell-cell, NODE, 0) → CRASH
```

The discrepancy with `last_cpr: s=1, val=0x0412d80e` suggests slot 1 is something
OTHER than the `*%binding-index-setup-max*` symbol (perhaps `#'%binding-index-area-callback`
function object or something accessed later in the function), and the symbol is at slot 0
(which was accessed first during the install-triggering ref, returned NIL, but the
`last_cpr` was NOT updated because the pool was not yet installed and the fast path
wasn't taken — OR was updated to NIL but then overwritten by a subsequent ref to slot 1).

---

## Summary of Questions

1. What are the decoded slot contents of entry 1115's 133-byte const pool? Which slot is `*%BINDING-INDEX-SETUP-MAX*`?
2. Does `wasm_find_package_named_bytes("CCL", 3)` succeed at Phase D time?
3. Does `wasm_find_symbol_named_bytes_scan` find `*%BINDING-INDEX-SETUP-MAX*` in the heap? If not, why?
4. What is `0x0412d80e` (the value at `last_cpr: s=1`)? Is it a symbol? Function? Something else?
5. Is the `wasm_find_symbol_named_bytes` fast path actually able to find symbols that were interned at xload (boot image creation) time?
6. If the fix is in `wasm_intern_startup`: should the function do a scan-all-packages lookup (`wasm_find_symbol_in_all_packages_bytes`) when both package-specific lookups fail, BEFORE the re-entrant guard synthesis path?

**Please do not modify any project files. Suggest fixes in your analysis report only.**
