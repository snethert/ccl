# WASM Calling Convention ABI

**Doc Version:** 1.0.0
**Date:** 2026-02-16
**Status:** Authoritative — all calling convention code must conform to this spec.

---

## Vstack Layout

- Grows **downward** (push = pre-decrement: `*--vsp = value`)
- `vsp[0]` = TOS = last item pushed
- `vsp[1]` = second-to-last item pushed
- Pop = post-increment: `value = *vsp++`

## Funcall Marshaling

**Source:** `wasm_funcall_common()` in `lisp-kernel/wasm-kernel-stubs.c`

For a Lisp call `(f arg0 arg1 ... argN-1)`:

1. Compiler emits `wasm_funcallN(fn, arg0, arg1, ..., argN-1)` with args in left-to-right (natural) order
2. `wasm_funcall_common` pushes args in **forward order** (args[0] first/deepest, args[N-1] at TOS):
   ```c
   for (signed_natural i = 0; i < count; i++) {
       *--vsp_ptr = args[i];
   }
   ```
3. Result: `vsp[0] = args[N-1]` (last Lisp arg), `vsp[N-1] = args[0]` (first Lisp arg)

**Same convention applies to:** `_SPksignalerr` push loop in `wasm-subprims-provider.c`

## Register Sync

**Source:** `wasm_sync_arg_regs_from_vsp()` in `lisp-kernel/wasm-subprims-provider.c`

After funcall pushes args to vstack, `_SPfuncall` syncs registers:

| Register | Source | Value | Meaning |
|----------|--------|-------|---------|
| `arg_z` | `vsp[0]` | `args[N-1]` | **Last** Lisp argument |
| `arg_y` | `vsp[1]` | `args[N-2]` | Second-to-last |
| `arg_x` | `vsp[2]` | `args[N-3]` | Third-to-last |
| `nargs` | set directly | `box_fixnum(N)` | Argument count |

This matches the **ARM32 convention**: arg_z = last arg, arg_y = first arg (for 2-arg calls).

## Compiled Function Argument Access

**Source:** `wasm_vsp_ref()` in `lisp-kernel/wasm-kernel-stubs.c`

Compiled functions access required arguments via `wasm_vsp_ref(index)`:

```c
value = vsp_ptr[count - 1 - index];
```

| Index | Returns | For 2-arg `(f a b)` |
|-------|---------|---------------------|
| 0 | First required arg | `a` |
| 1 | Second required arg | `b` |
| N-1 | Last required arg | (last) |

The `count - 1 - index` formula maps natural argument indices (0 = first) to the reversed vstack layout (vsp[0] = last).

**Default path:** `*wasm2-use-arg-regs*` = `nil` (line 1531 of `wasm2.lisp`). All compiled functions use `wasm_vsp_ref` for argument access. Arg registers (arg_z, arg_y) are NOT read by compiled function bodies.

## Inline Subprim Calls

**Source:** `:set-arg0/1/2` IR opcodes in `compiler/WASM/wasm2.lisp`

For direct subprim calls (e.g., `_SPmisc_alloc` from `wasm2-%alloc-misc`):

| IR Opcode | C Function | TCR Register |
|-----------|------------|-------------|
| `:set-arg0` | `wasm_set_arg_z()` | `arg_z` |
| `:set-arg1` | `wasm_set_arg_y()` | `arg_y` |
| `:set-arg2` | `wasm_set_arg_x()` | `arg_x` |

These write TCR registers **directly** — they bypass the vstack entirely. The argument semantics are per-subprim (e.g., `_SPmisc_alloc`: arg_z = subtag, arg_y = count).

## Memory Access: wasm_lisp_word_ref

**Source:** `wasm_lisp_word_ref()` in `lisp-kernel/wasm-kernel-stubs.c`

General-purpose tagged memory read used by the WASM compiler for `%car`, `%cdr`, `%svref`, `%slot-ref`, `typecode`, `%fixnum-ref`, and `%lisp-word-ref`.

Dispatch by fulltag of `base`:

| Base tag | idx semantics |
|----------|---------------|
| nil | Always returns nil |
| fulltag_cons | idx 0 = cdr (struct offset 0), idx 1 = car (struct offset 4) |
| fulltag_misc | idx -1 = header word, idx 0+ = data slot N (deref at N+1) |
| tag_fixnum | Raw address: `ptr[idx]` (unboxed pointer arithmetic) |

### Cons cell layout

Canonical definition in `constants.h:41-44`:

```c
typedef struct cons {
  LispObj cdr;    /* offset 0, word 0 */
  LispObj car;    /* offset 4, word 1 */
} cons;
```

Lisp definition in `wasm-arch.lisp:335`: `(define-lisp-object cons fulltag-cons cdr car)`

JS constants in `ccl-loader.mjs`: `CONS_CDR_OFFSET = 0`, `CONS_CAR_OFFSET = 4`

The compiler emits `%cdr` as `lisp-word-ref(cons, box_fixnum(0))` and `%car` as `lisp-word-ref(cons, box_fixnum(1))`. Mutation goes through `_SPrplaca` / `_SPrplacd` subprims which use struct field access directly.

## Known Issues

### Latent bug: `:arg0` register mapping (DISABLED)

The compiler maps `:arg0` -> `wasm_get_arg_z()` and `:arg1` -> `wasm_get_arg_y()`. This treats arg_z as the **first** required argument. But after register sync, arg_z = **last** argument (ARM convention).

**Impact:** None currently. `*wasm2-use-arg-regs*` = `nil`, so this code path is never taken. **Must fix before enabling arg-regs optimization.**

**Fix when needed:** For a 2-arg function, map first required arg to arg_y (not arg_z), matching ARM convention. Or reverse the sync to put first arg in arg_z (breaking ARM compatibility).

## Implementation Sites (Exhaustive)

| Site | File | Line | Role |
|------|------|------|------|
| Push loop | `wasm-kernel-stubs.c` | ~2106 | Pushes args to vstack |
| Register sync | `wasm-subprims-provider.c` | ~1640 | vsp → arg_z/y/x |
| Compiler funcall | `wasm2.lisp` | ~3619 | Emits wasm_funcallN params |
| vsp_ref | `wasm-kernel-stubs.c` | ~1676 | Compiled code reads args |
| set-arg direct | `wasm2.lisp` | ~5847 | Inline subprim arg setup |
| Error push | `wasm-subprims-provider.c` | ~384 | _SPksignalerr args |
| Function entry | `wasm2.lisp` | ~2113 | Binds args to locals |
| Arg-regs (disabled) | `wasm2.lisp` | ~5822 | :arg0/:arg1 register read |
