# Capability Negotiation (WASM)

**Status:** Draft  
**Scope:** Defines how the Lisp runtime and microkernel discover and use host
capabilities in a portable way.

## Goals

- Provide a minimal, explicit capability handshake.
- Map missing capabilities to `CAPABILITY-UNAVAILABLE` conditions.
- Keep the ABI stable while allowing future expansion.

## Baseline Mechanism: `KERNEL_OP_CAPS`

`kernel_request` opcode `KERNEL_OP_CAPS` returns:

```
abi_version        u32
capability_bits    u32
max_response_bytes u32
reserved           u32
```

### Capability bits (current)

- bit 0 — requests may return `PENDING` (Stage‑2 async)
- bit 1 — `kernel_wait` implemented (Stage‑3)
- bit 2 — shared memory/Atomics available
- bit 3 — zero‑copy response variants available

See `doc/wasm/kernel-request-abi.md:120` for the current registry.

## Lisp Runtime Policy

**MVP rule:** if an operation depends on a missing capability, signal a
`CAPABILITY-UNAVAILABLE` condition with:

- `:capability` keyword
- `:operation` string/symbol
- optional `:details`

**Current hook:** `ccl::*capability-unavailable-on-enosys*` causes stream I/O
errors that surface `ENOSYS` or `EACCES` to signal `CAPABILITY-UNAVAILABLE`.

**Recommended bring‑up behavior:**

1. Call `wasm_kernel_caps` at startup.
2. Set runtime flags based on the capability bits.
3. Enable `*capability-unavailable-on-enosys*` when `:io/stream` is missing.

## Capability Keys (Canonical)

See `doc/wasm/capability-matrix.md:14`.

## Open Questions

- Should capability discovery be static (config file) or dynamic (query)?
- Should the microkernel expose a structured capability map beyond bitflags?
- How should Lisp request optional features (e.g., `:fs/virtual`) at runtime?
