# Codex Read-Only Analysis Request: CCL WASM32 FASL Loading Failure

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find.**

---

## The System

Clozure Common Lisp (CCL) compiled to WASM32. The build system:

1. Cross-compiles level-0 Lisp sources → boot WASM modules + boot image
2. Cross-compiles level-1 Lisp sources → runtime WASM modules + `.lafsl` FASL files
3. `make-real-image.mjs` assembles everything into `root.image`

Build flow in `scripts/wasm/lib/make-real-image.mjs`:

1. Load boot image into WASM memory
2. Install compiled WASM modules (boot + runtime) into function table
3. Image fixup: scan boot-image symbols, match to named entries, patch entry indices in function objects
4. `wasm_run_cold_boot_init()` — infrastructure setup + cold-load drain
5. FASL loading — load level-1 `.lafsl` files via `wasm_fasload_path()`
6. Force-rebind, invariant gate, GC, save image

## The Failure

Step 5 fails. Every FASL load triggers:

```
funcall-err: code=6 name=0x0400016e tag=6 hdr=0x0000073a subtag=58 fcell=0x04110006 sym=%KERNEL-RESTART Rfn=0x0400016e
```

- `code=6` = `WASM_XFUNBND` (function unbound), defined at `wasm-subprims-provider.c:353`
- `subtag=58` = `0x3A` = `subtag_symbol` (node subtag 7), defined at `wasm-arch.lisp:301`
- `fcell=0x04110006` = the UDF (undefined function) stub
- This error repeats identically for all 16 FASL files loaded

Step 4 (cold-load drain) also hits 3 errors:
```
cold-load-drain: 62 called, 3 errors, 0 skipped
```
First error: `WASM_XFUNBND` on `%DEFVAR`. Second/third: `HASH-TABLE` unbound.

## Observed Facts

### Fact 1: These functions are level-1 only

```
$ grep -rn 'defun %kernel-restart\b' level-0/ level-1/
level-1/l1-error-signal.lisp:19:(defun %kernel-restart (error-type &rest args)

$ grep -rn 'defun %defvar' level-0/ level-1/
level-1/l1-utils.lisp:200:(defun %defvar (var &optional doc)
```

Neither `%KERNEL-RESTART` nor `%DEFVAR` is defined in any level-0 file.

### Fact 2: Level-0 code calls these functions

```
$ grep -rn '%kernel-restart' level-0/
level-0/l0-pred.lisp:1014:    (%kernel-restart $xwrongtype arg ...)
level-0/l0-symbol.lisp:134:      (%kernel-restart $xvunbnd sym)
level-0/nfasload.lisp:338:    (set-package (%kernel-restart $xnopkg name))))
level-0/nfasload.lisp:382:                     (errorp (%kernel-restart $xnopkg xthing)))))
level-0/nfasload.lisp:388:      (%epushval s (or p (%kernel-restart $XNOPKG ...)))
level-0/nfasload.lisp:393:      (%epushval s (or p (%kernel-restart $XNOPKG ...))))
```

### Fact 3: Boot image is dumped before level-1 compilation

Build log shows the boot image dump (`heap-image.lisp` load) occurs at line 391, after all level-0 files (lines 271-375) but before any level-1 compilation.

### Fact 4: These functions are in runtime modules, not boot modules

```
Boot modules: 2189 functions, entry range 202-1413
Runtime modules: 4756 functions, entry range 1421-8971
No overlap.

%DEFVAR = runtime entry 1495 (not in boot modules)
%KERNEL-RESTART = runtime entry 8312 (not in boot modules)
```

### Fact 5: Image fixup only uses boot module entries

`make-real-image.mjs` lines 1222-1230:
```javascript
  // Collect named functions for image fixup.
  // IMPORTANT: only use BOOT module entries here.  Runtime (level-1) module
  // entries must NOT override boot stubs during image fixup because their
  // initialization (defvar, defclass, etc.) hasn't run yet — that happens
  // later during FASL loading.
  const allNamedFunctions = [
    ...bootNamedFunctions,
  ];
```

Runtime entries are excluded. The rebindMap used for image fixup has 1105 entries (boot only).

### Fact 6: Image fixup results

```
[stage] image fixup: 1018 in-place + 69 new-alloc / 1105 total (10756 syms, 0 skipped, 18 unmatched)
```

10756 symbols in boot image. 1105 matched to boot module entries and patched. The remaining ~9651 symbols are untouched.

### Fact 7: Cold-boot-init reaches step 90

```
cold-boot-init: ok, startup-step=90
```

All infrastructure setup completed (locks, class cells, package rehash, binding indices).

### Fact 8: FASL loading calls %KERNEL-RESTART from nfasload.lisp

The `%FASLOAD` function (level-0/nfasload.lisp:968) is the FASL loader. It's called from C via `wasm_fasload_path()`. During loading, FASL opcodes like `$fasl-vpackage` and `$fasl-nvpackage` look up packages. If a package isn't found, they call `%kernel-restart`:

```lisp
;; nfasload.lisp:338
(set-package (%kernel-restart $xnopkg name))
```

### Fact 9: defvar macro expands to call %defvar

`lib/macros.lisp:731-745`:
```lisp
(defmacro defvar (&environment env var &optional (value () value-p) doc)
  `(progn
    (eval-when (:compile-toplevel) (note-variable-info ',var ,value-p ,env))
    ,(if value-p
       `(%defvar-init ,var ,value ,doc)
       `(%defvar ',var))
    ',var))
```

Cold-load functions from level-0 files that contain `defvar` forms generate code that calls `%defvar` at execution time.

### Fact 10: The UDF stub has entry index 131

From diagnostic output: `fcell=0x04110006 ent=0x0000020c`. Entry = 0x020c >> 2 = 131.

## Questions for Codex

### Q1: Native CCL Cold Boot

In native CCL (ARM64, x86-64), the same boot image is used. `%KERNEL-RESTART` and `%DEFVAR` are also level-1 functions, also not in the boot image.

**Trace the native CCL cold-boot sequence and determine:**
- What is in `%KERNEL-RESTART`'s fcell when the native boot image is loaded?
- What is in `%DEFVAR`'s fcell when the native boot image is loaded?
- If they are UDF: how does native CCL handle the call to an undefined function during cold boot? What does the ARM64 UDF trap handler do?
- If they are NOT UDF: when and how do their fcells get populated during cross-compilation?

**Files to examine:**
- `lisp-kernel/arm-spentry.s` — `_SPfuncall`, UDF handling
- `lisp-kernel/arm-exceptions.c` — trap handlers
- `lisp-kernel/pmcl-kernel.c` — `cold_boot`, `%TOPLEVEL-FUNCTION%` dispatch
- `xdump/heap-image.lisp` — boot image dump procedure
- `xdump/xfasload.lisp` — cross-loader, symbol/fcell setup
- `lib/compile-ccl.lisp` — cross-compilation orchestration
- `level-0/l0-init.lisp` — native cold boot entry

### Q2: Cross-Compilation Image Contents

**Determine what the cross-compiler puts in symbol fcells for level-1 functions:**
- Does the cross-compiler create xfunction objects for level-1 functions?
- Are those xfunctions stored in the boot image symbol fcells?
- Or does the boot image only contain fcells for functions defined in level-0?
- Trace the path: `defun %kernel-restart` in `l1-error-signal.lisp` → what does the cross-compiler do with it? Does `%defun` during cross-compilation store an xfunction in the target symbol's fcell?

**Files to examine:**
- `compiler/WASM/wasm2.lisp:7700-7716` — xfunction creation during cross-compilation
- `xdump/xfasload.lisp` — how the cross-loader processes `$fasl-defun`
- `level-0/l0-def.lisp` — `%defun` implementation
- `lib/nfcomp.lisp` — FASL compiler, how defun generates FASL opcodes

### Q3: Level-1 FASL Loading on Native CCL

**Determine how native CCL loads level-1 FASLs during cold boot:**
- Does `%FASLOAD` call `%KERNEL-RESTART` during normal FASL loading on native ARM?
- If so, what provides `%KERNEL-RESTART` at that point?
- Is there a different FASL loading path for cold boot vs. normal runtime?
- Does the native kernel provide any fallback for undefined functions called during FASL loading?

**Files to examine:**
- `level-0/nfasload.lisp` — `%FASLOAD`, all `%kernel-restart` call sites
- `level-1/l1-boot-2.lisp` — level-1 boot sequence
- `level-0/l0-init.lisp` — `%TOPLEVEL-FUNCTION%`

### Q4: FASL Loading Trigger

**Determine which specific FASL opcode triggers the `%KERNEL-RESTART` call:**
- Which opcode handler in `nfasload.lisp` is called first when loading a level-1 `.lafsl`?
- Is `%KERNEL-RESTART` called because a package lookup fails? If so, which package?
- Or is it called for a different reason (type check failure, etc.)?
- Is this call inherent to every FASL file, or only triggered by specific content?

### Q5: Build System Question

**Determine if the WASM build flow matches native CCL's build flow:**
- In native CCL, is level-1 compiled before or after the boot image dump?
- If level-1 is compiled before the image dump (in native CCL), are level-1 function xfunctions included in the native boot image?
- Does the WASM build system (`rebuild-everything.sh`) compile level-1 in the same relative order as native CCL?
- Is there a discrepancy in build ordering between native and WASM that explains why level-1 functions are missing from the WASM boot image?

**Files to examine:**
- `scripts/wasm/rebuild-everything.sh` — WASM build flow
- `lib/compile-ccl.lisp` — native cross-compilation flow
- `xdump/heap-image.lisp` — when image dump happens relative to level-1 compilation

## Relevant Definitions

```
subtag_function     = 0x2A  (wasm-arch.lisp:299, node subtag 5)
subtag_xfunction    = 0x92  (wasm-arch.lisp:312, node subtag 18)
subtag_symbol       = 0x3A  (wasm-arch.lisp:301, node subtag 7)
WASM_XFUNBND        = 6     (wasm-subprims-provider.c:353)
WASM_XNOTFUN        = 13    (wasm-subprims-provider.c:354)
canonical-nil-value = 0x04000001
fulltag_misc        = 6
fulltag_nil         = 1
```

## Output Format

Report findings as facts with file:line citations. For each question, state what you found and where. If a question cannot be answered from the codebase, state that explicitly.

**Do not modify any files. Do not write patches. Report only.**
