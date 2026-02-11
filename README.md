# Clozure CL

This is the source code for Clozure CL.

Because CCL is written in itself, you need an already-working version
of CCL to compile it.

See https://github.com/Clozure/ccl/releases/latest for instructions
on how to get a copy of CCL for your system.

To report a bug or request an enhancement, please make an issue at
https://github.com/Clozure/ccl/issues.

If you have questions or run into problems, send mail to
ccl-devel@clozure.com (see https://lists.clozure.com for instructions
on how to subscribe), ask on #ccl on libera.chat, or create an
issue here, especially if you think you have found a bug.

## WASM Kernel Build

### Why `make` can fail after `source scripts/wasm/env.sh`

If `CC` from `scripts/wasm/env.sh` is not honored, builds compile without WASI
headers and fail with errors like:

- `fatal error: 'errno.h' file not found`
- `fatal error: 'stdio.h' file not found`

The wasm makefiles in this tree now use `CC ?= clang`, so `source
scripts/wasm/env.sh` is honored by plain `make`.

If you are on an older branch where `CC = clang` is still hard-set, use the
command-line override form (`CC="$CC"`).

### Build The Kernel

**IMPORTANT (macOS/Homebrew):** source the toolchain env first.

```bash
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32 clean
make -C lisp-kernel/wasm32
```

Explicit override form (works on old/new makefiles):

```bash
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32 clean
make -C lisp-kernel/wasm32 CC="$CC" WASM_LD="$WASM_LD"
```

Build output:

- `doc/wasm/js/wasmcl.wasm`

Linux (`wasm32-wasi` toolchains):

```bash
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi clean
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi
```

### Build The Subprims Provider (Scaffold)

Optional separate provider module:

```bash
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi clean
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi
```

`WASM_TARGET=wasm32-wasi` assumes a toolchain/sysroot setup that provides WASI
headers. Without that setup, it can fail with missing libc headers.

On macOS (after `source scripts/wasm/env.sh`):

```bash
make -C lisp-kernel/wasm32/subprims clean
make -C lisp-kernel/wasm32/subprims
```

Explicit override form:

```bash
make -C lisp-kernel/wasm32/subprims clean
make -C lisp-kernel/wasm32/subprims CC="$CC"
```

The JS host should only call `wasm_set_subprims_ready(1)` when the provider
exports Tier 0 subprims (`_SPmkcatch1v`, `_SPfuncall`, `_SPnthrow1value`).

### Verify No WASI Runtime Imports

```bash
wasm-objdump -x doc/wasm/js/wasmcl.wasm | rg 'wasi_snapshot_preview1' || true
```

Optional check for the subprims provider:

```bash
wasm-objdump -x doc/wasm/js/subprims.wasm | rg 'wasi_snapshot_preview1' || true
```
