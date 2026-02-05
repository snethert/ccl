# Kernel Opcode Registry (kernel_request)

**Status:** Draft  
**Scope:** Canonical registry for `kernel_request` opcodes and stream kinds.
Detailed layouts remain in `doc/wasm/kernel-request-abi.md`.

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

## Stream Kinds (STREAM_OPEN)

| Kind | Name | Status | Notes |
|---:|---|---|---|
| `0` | `PIPE` | Implemented | In‑memory FIFO |
| `1` | `NAMED_RO` | Implemented | Read‑only named byte source |

## Versioning

- ABI version is reported by `KERNEL_OP_CAPS`.
- Add new opcodes by extending this registry and updating `kernel-request-abi.md`.
