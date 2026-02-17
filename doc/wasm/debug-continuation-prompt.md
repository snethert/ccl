# Debug Continuation Prompt — Root Image Infinite Loop

**Use this as the starting prompt for a new Claude Code session to continue debugging.**

---

## Prompt

Resume work on the CCL WASM port TODOs. Read `TODO.md` first. The current blocker is an **infinite loop during root image build** (Phase 1).

### What was fixed this session

**Bug 1 — Funcall argument ordering (FIXED, committed `31d89be7`):**

`wasm_funcall_common()` in `lisp-kernel/wasm-kernel-stubs.c:2106` was pushing arguments to the vstack in the wrong order. The push loop `for (i = count-1; i >= 0; i--)` put args[0] (first Lisp arg) at TOS (vsp[0]), which then mapped to arg_z. But CCL convention requires arg_z = LAST arg, arg_y = FIRST arg.

Fix: changed to `for (i = 0; i < count; i++)` so args[0] is pushed first (deepest) and args[count-1] is at TOS → arg_z = last arg. Same fix applied to `_SPksignalerr` push loop in `lisp-kernel/wasm-subprims-provider.c:384`.

**Bug 2 — FASL loading regression (was ALREADY fixed by prior commits):**

The `fn=0x2c` (fixnum 11 where function expected) bug was fixed by `%car/%cdr` slot index swap in `compiler/WASM/wasm2.lisp`. The system now loads packages and calls Lisp functions successfully.

**Diagnostics removed (committed `31d89be7`):**
- Removed per-call `DIAG: cfv` logging from `wasm_call_function_value` (was logging EVERY function dispatch, caused OOM)
- Removed `DIAG: funcall1` logging from `wasm_funcall1`
- Removed `DIAG: spill_pop 0x2c` check
- Removed `wasm_cfv_depth` tracking
- Added `--max-old-space-size=8192` to Node.js invocation in `rebuild-everything.sh`

### Current blocker — Infinite loop after packages load

After the funcall fix, the root image build (`scripts/wasm/rebuild-everything.sh`) no longer crashes at `_SPmisc_alloc`. Instead, it **hangs indefinitely** at 100% CPU with stable ~811MB RSS.

**Last stderr output before hang:**
```
DIAG: %all-packages% sym=0x040003ae val=0x041101bd
DIAG: pkg[0] elem=0x04110016 ft=6 sub=0x00000062 cnt=8 s0=0x0412f46d s1=0x0412f3b5
DIAG: pkg[1] ... (6 packages found, all with sub=0x62=subtag_package, cnt=8)
DIAG: cpi fix e=1123 i=20 tag=6 val=0x0
DIAG: cpi fix e=1123 i=26 tag=6 val=0x100
(hangs here — no more output, 100% CPU, stable memory)
```

The `cpi fix` messages come from `lisp-kernel/wasm-kernel-stubs.c:5204` — the const pool install function detecting fixnum-tagged values in pool slots. Entry 1123 is the function being processed when it stalls.

**What this means:** The system successfully finds 6 packages, installs const pools, and then enters an infinite loop. The loop is in compiled Lisp code (not C), because the C-side diagnostics stop producing output.

### Key investigation paths

1. **Identify entry 1123**: What function has entry index 1123? Check the boot module manifest at `build/wasm32/modules/wasm-boot-modules.json` or `build/wasm32/modules/wasm-runtime-modules.json` for function name → entry index mapping.

2. **Add targeted diagnostic**: In `wasm_call_function_value` (`wasm-subprims-provider.c:~2020`), add a CONDITIONAL diagnostic that only fires after the `cpi fix` messages (e.g., only log calls to entry 1123 or calls happening after a global counter exceeds N). Do NOT log every call — that causes OOM.

3. **Check for argument-order-dependent infinite loops**: The funcall argument swap fix may have FIXED some multi-arg calls but BROKEN others if some code was accidentally adapted to the wrong ordering. Look for `wasm_funcall2` / `wasm_funcall3` callers in the JS host code (`scripts/wasm/lib/`) that may pass arguments in the wrong order to compensate.

4. **Check `wasm2-emit-call` argument order**: In `compiler/WASM/wasm2.lisp:3619-3631`, the compiler evaluates arguments left-to-right and passes them as WASM function parameters to `wasm_funcallN`. After our fix, args[0]=first Lisp arg gets pushed deepest (→arg_y for 2-arg). Verify this matches what compiled Lisp code expects.

5. **Remaining DIAG messages**: There are still diagnostic messages in `wasm-kernel-stubs.c` (lwref tracing at lines 1345-1413, %all-packages% dump at lines 3203-3265, cpi fix at line 5204). These are conditional and shouldn't cause OOM but add overhead. Consider removing them after debugging.

### Key files

| File | Purpose |
|------|---------|
| `TODO.md` | Task tracking — update when progress is made |
| `lisp-kernel/wasm-kernel-stubs.c` | Kernel C stubs — `wasm_funcall_common` (line 2106), spill push/pop, const pool install |
| `lisp-kernel/wasm-subprims-provider.c` | Subprims module — `_SPfuncall`, `wasm_call_function_value`, `_SPmisc_alloc`, `wasm_sync_arg_regs_from_vsp` |
| `compiler/WASM/wasm2.lisp` | WASM compiler backend — `wasm2-emit-call` (line 3515), `wasm2-%alloc-misc` (line 3330) |
| `scripts/wasm/lib/make-real-image.mjs` | Root image builder (the Node.js process that hangs) |
| `scripts/wasm/rebuild-everything.sh` | Full rebuild script |
| `build/wasm32/modules/wasm-boot-modules.json` | Boot module manifest (entry index → function name mapping) |
| `build/wasm32/modules/wasm-runtime-modules.json` | Runtime module manifest |
| `doc/wasm/debugging.md` | Debugging guide |

### Build & test commands

```bash
# Full rebuild (kernel + subprims + boot image + modules + root image):
scripts/wasm/rebuild-everything.sh

# Root image only (after kernel/modules are built):
node --max-old-space-size=8192 scripts/wasm/lib/make-real-image.mjs \
  --output build/wasm32/images/root.image \
  --manifest-out build/wasm32/images/root.image.manifest.json \
  --modules build/wasm32/modules/wasm-runtime-modules.json \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json

# Capture stderr separately to see diagnostics:
node ... 2>/tmp/root-image-stderr.log

# Phase 0AA bridge tests:
node scripts/wasm/tests/phase0a-bridge-smoke.mjs

# Kernel-only rebuild:
make -C lisp-kernel/wasm32

# Subprims-only rebuild:
make -C lisp-kernel/wasm32/subprims clean all
```

### Architecture reminders

- **Two-module WASM**: Kernel (`wasmcl.wasm`) and subprims (`subprims.wasm`) are separate WASM modules. No libc in subprims — use inline formatting for diagnostics there.
- **ARM32 reference**: WASM target is based on ARM32. Check `compiler/ARM/arm2.lisp` and `lisp-kernel/arm/` first when investigating compiler/runtime bugs.
- **CCL calling convention**: arg_z = last arg (vsp[0]), arg_y = second-to-last (vsp[1]), arg_x = third-to-last (vsp[2]). fixnumshift=2, tag_fixnum=0.
- **snprintf policy**: Use hand-rolled formatting in subprims (no libc). Use `snprintf` only for numeric formats in kernel stubs.
- **Always rebuild before investigating runtime bugs** — stale artifacts cause misleading failures.
