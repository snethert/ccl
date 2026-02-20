# Kernel Opcode Registry (kernel_request)

**Status:** Draft
**Scope:** Canonical registry for `kernel_request` opcodes and stream kinds.
Detailed layouts remain in `doc/wasm/kernel-request-abi.md`.
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

## Reserved Ranges

- `0x0000_0000` – `0x0000_FFFF`: core opcodes (this document)
- `0x8000_0000` – `0xFFFF_FFFF`: experimental/vendor opcodes (must be documented)

## Core Opcodes (v1)

| Opcode | Name | Status | Notes |
|---:|---|---|---|
| `0x0000_0000` | `KERNEL_OP_CAPS` | Implemented | Capability discovery |
| `0x0000_0001` | `KERNEL_OP_LOG` | Implemented | Host log sink |
| `0x0000_0002` | `KERNEL_OP_STREAM_WRITE` | Implemented | Stdout/stderr + stream SIDs |
| `0x0000_0003` | `KERNEL_OP_STREAM_READ` | Implemented | Stdin + stream SIDs |
| `0x0000_0004` | `KERNEL_OP_TIME_NOW` | Implemented | Unix ms |
| `0x0000_0005` | `KERNEL_OP_STREAM_OPEN` | Implemented | `PIPE`, `NAMED_RO` |
| `0x0000_0006` | `KERNEL_OP_STREAM_CLOSE` | Implemented | Close stream SID |
| `0x0000_0007` | `KERNEL_OP_COMPILED_MODULES_REFRESH` | Draft | Refresh compiled module registry |
| `0x0000_0008` | `KERNEL_OP_FS_PROBE` | Implemented | Persistence service |
| `0x0000_0009` | `KERNEL_OP_FS_TRUENAME` | Implemented | Persistence service |
| `0x0000_000A` | `KERNEL_OP_FS_DIRECTORY` | Implemented | Persistence service |
| `0x0000_000B` | `KERNEL_OP_FS_FILE_WRITE_DATE` | Implemented | Persistence service |
| `0x0000_000C` | `KERNEL_OP_FS_RENAME` | Implemented | Persistence service |
| `0x0000_000D` | `KERNEL_OP_FS_DELETE` | Implemented | Persistence service |
| `0x0000_000E` | `KERNEL_OP_FS_ENSURE_DIRS` | Implemented | Persistence service |
| `0x0000_000F` | `KERNEL_OP_FS_DELETE_EMPTY_DIR` | Implemented | Persistence service |
| `0x0000_0010` | `KERNEL_OP_FS_DELETE_TREE` | Implemented | Persistence service |
| `0x0000_0011` | `KERNEL_OP_STREAM_SEEK` | Implemented | File streams only |
| `0x0000_0012` | `KERNEL_OP_STREAM_TRUNCATE` | Implemented | File streams only |
| `0x0000_0020` | `KERNEL_OP_UI_POLL` | Draft | Poll UI event batch |
| `0x0000_0021` | `KERNEL_OP_UI_RENDER` | Draft | Submit UI render tree/patch |
| `0x0000_0022` | `KERNEL_OP_UI_MEASURE_TEXT` | Draft | Text measurement |
| `0x0000_0023` | `KERNEL_OP_RUNTIME_EVENT` | Draft | Runtime bridge JSON payload |
| `0x0000_0024` | `KERNEL_OP_RUNTIME_COMMAND_POLL` | Draft | Poll runtime command queue |

## Stream Kinds (STREAM_OPEN)

| Kind | Name | Status | Notes |
|---:|---|---|---|
| `0` | `PIPE` | Implemented | In‑memory FIFO |
| `1` | `NAMED_RO` | Implemented | Read‑only named byte source |
| `2` | `FILE` | Implemented | Persistence service file stream |

## Cross-Language Validation

All opcode values and status codes are validated by the ABI contract system.
The generator (`scripts/wasm/generate_abi_contract.py`) extracts canonical values
from `lisp-kernel/wasm-host.h` and produces validation files for C (`_Static_assert`),
JS (ES module imports in `abi-constants.mjs`), and Python. Any opcode drift between
C and JS is caught at build time.

## Versioning

- ABI version is reported by `KERNEL_OP_CAPS`.
- Add new opcodes by extending this registry, updating `kernel-request-abi.md`, and re-running `python3 scripts/wasm/generate_abi_contract.py`.
