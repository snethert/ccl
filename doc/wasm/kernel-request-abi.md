# Kernel Request ABI (WASM Imports)

**Status:** Draft (MVP, copy-based responses)

## Scope

This document defines the **guest↔host ABI** used by a WASM runner (the Lisp
kernel/runtime) to request external services from the JavaScript microkernel.

It specifies:

- the required WASM imports and their semantics,
- request lifecycle and error conventions,
- the MVP response transfer mechanism (copy-based),
- an initial opcode registry and payload/response layouts.

It does **not** define the internal Lisp/kernel interfaces (e.g. CCL
`KERNEL_IMPORTS`), nor does it prescribe a particular Lisp execution model
(single runner vs multi-runner).

## Conventions

- **Endianness:** all integer fields are **little-endian**.
- **Types:** `u32`, `i32`, `u64` refer to fixed-width integers in the payload
  byte stream.
- **Pointers:** `payloadPtr`, `dstPtr` are offsets into the runner's **linear
  memory** (`env.memory`).
- **Strings:** UTF-8 bytes, **not** NUL-terminated unless explicitly stated.

## Import module and functions

All functions below are imported from the WASM module namespace `ccl`.

### Required imports (MVP)

- `kernel_request(opcode: u32, payloadPtr: u32, payloadLen: u32) -> requestId: u32`
- `kernel_poll(requestId: u32) -> status: u32`
- `kernel_result(requestId: u32) -> result: i32`
- `kernel_response_size(requestId: u32) -> nbytes: u32`
- `kernel_copy_response(requestId: u32, dstPtr: u32, dstLen: u32) -> copied: u32`
- `kernel_drop_request(requestId: u32) -> void`

### Optional import (Stage 3 optimization)

- `kernel_wait(requestId: u32, deadlineMs: i32) -> status: u32`

`deadlineMs` conventions (if implemented):

- `-1`: wait indefinitely
- `0`: do not block (equivalent to `kernel_poll`)
- `>0`: wait up to `deadlineMs` milliseconds

## Interrupt ABI (host-side flags)

Interrupt delivery is **cooperative** in the baseline WASM model. There is no
`kernel_request` opcode for interrupts in the MVP. Instead:

- The host requests an interrupt by **setting the runner's interrupt_pending flag**
  in the TCR (or equivalent runtime structure in linear memory).
- The runner **polls at safepoints** and at explicit stepping boundaries
  (`wasm_ccl_step`) to deliver the interrupt.

This keeps the ABI stable for the portable baseline. A future extension may
add an explicit `KERNEL_OP_INTERRUPT` opcode, but it is not required for MVP.

## Request lifecycle (required)

1. Guest calls `kernel_request(...)` and receives a non-zero `requestId`.
2. Guest checks completion via `kernel_poll(requestId)` (or `kernel_wait` if available).
3. When complete, guest reads:
   - `kernel_result(requestId)` for the operation’s primary result, and
   - `kernel_response_size`/`kernel_copy_response` for any response payload bytes.
4. Guest calls `kernel_drop_request(requestId)` **exactly once** to release all
   host-side state associated with the request.

After `kernel_drop_request`, the `requestId` becomes invalid and may be reused.

**Implementation note (reference microkernel):** `kernel_drop_request` is
idempotent (repeated drops are ignored). Guests must still follow the ABI rule
and drop each request exactly once; idempotence is a safety net for bring-up.

## Status codes

`kernel_poll` and `kernel_wait` return one of:

- `KERNEL_STATUS_PENDING = 0`
- `KERNEL_STATUS_DONE    = 1`
- `KERNEL_STATUS_ERROR   = 2`

Notes:

- `DONE` means the request has a final `kernel_result` (success or failure).
- `ERROR` is reserved for “transport/ABI-level” failure modes (invalid request
  ID, malformed payload, capability violation). In this case,
  `kernel_result(requestId)` MUST return a negative errno-style value (e.g.
  `-EINVAL`).

## Result and error conventions

`kernel_result(requestId)` returns an `i32`:

- On success: **non-negative**, opcode-defined (e.g. byte count).
- On failure: **negative errno** (e.g. `-ENOSYS`, `-EINVAL`, `-EWOULDBLOCK`).

The microkernel MUST NOT throw JS exceptions for ordinary operation failures.
Use negative errno returns instead. JS exceptions are reserved for fatal host
bugs during development.

### Errno number compatibility

The runner and microkernel MUST agree on the numeric values used for errno.
For the current bring-up builds that compile with `--target=wasm32-wasi`,
implementations SHOULD use the values from the toolchain's `errno.h`
(wasi-libc / WASI errno numbers), not host-platform (Linux/macOS) errno values.

## Response payload (copy-based, MVP)

The microkernel may associate an optional response byte buffer with each
request. The guest obtains it by:

1. Calling `kernel_response_size(requestId)` to get the exact size.
2. Allocating a buffer of that size in linear memory.
3. Calling `kernel_copy_response(requestId, dstPtr, dstLen)` to copy the bytes.

Requirements:

- If `dstLen >= kernel_response_size(requestId)`, `kernel_copy_response` MUST
  copy the full response and return `copied == response_size`.
- The response buffer remains valid (host-owned) until `kernel_drop_request` is
  called.
- If an opcode defines a response payload and returns a non-negative byte
  count, the response size MUST be consistent with that return value (see per-opcode rules).

### Zero-copy responses (TODO)

The MVP response path is copy-based: the microkernel retains each response
payload in host memory and copies it into the runner's linear memory on demand
via `kernel_copy_response`. This keeps the ABI simple and portable.

TODO(zero-copy): Provide optional ABI extensions that avoid this copy by writing
responses directly into guest linear memory (caller-provided output buffers or a
shared arena/ring buffer). Any zero-copy form MUST define explicit lifetime and
invalidation rules and MUST remain optional; the copy-based path remains the
required baseline for correctness and broad compatibility.

**Implementation note:** JS and C implementations SHOULD include explicit
`TODO(zero-copy)` comments near the copy boundary to keep this planned
optimization visible.

## Opcode registry (initial)

All opcodes are `u32`.

- `KERNEL_OP_CAPS         = 0x0000_0000`
- `KERNEL_OP_LOG          = 0x0000_0001`
- `KERNEL_OP_STREAM_WRITE = 0x0000_0002`
- `KERNEL_OP_STREAM_READ  = 0x0000_0003`
- `KERNEL_OP_TIME_NOW     = 0x0000_0004`
- `KERNEL_OP_STREAM_OPEN  = 0x0000_0005`
- `KERNEL_OP_STREAM_CLOSE = 0x0000_0006`
- `KERNEL_OP_COMPILED_MODULES_REFRESH = 0x0000_0007`
- `KERNEL_OP_UI_POLL      = 0x0000_0020`
- `KERNEL_OP_UI_RENDER    = 0x0000_0021`
- `KERNEL_OP_UI_MEASURE_TEXT = 0x0000_0022`

Unrecognized opcodes MUST complete with `kernel_result == -ENOSYS`.

## Payload and response formats

All payloads are byte strings starting at `payloadPtr` with length `payloadLen`.
Unless otherwise specified, payload headers are laid out as packed little-endian
integers at offset 0.

### `KERNEL_OP_CAPS`

Payload: empty (`payloadLen = 0`).

Response payload (`kernel_response_size = 16`):

```
offset  size  field
0x00    u32   abi_version          (currently 1)
0x04    u32   capability_bits
0x08    u32   max_response_bytes   (0 if unknown/unlimited)
0x0c    u32   reserved             (0)
```

Initial `capability_bits` allocation (others reserved, must be 0 for now):

- bit 0: requests may return PENDING (Stage 2+)
- bit 1: `kernel_wait` is implemented and usable (Stage 3)
- bit 2: shared memory/Atomics available (environment-dependent)
- bit 3: zero-copy response variants available (TODO)

**Implementation note (reference microkernel):** capability bit 0 is set when the
microkernel is configured to allow PENDING requests (currently `asyncStdin: true`
and only for stdin `STREAM_READ`).

`kernel_result`: `0` on success; negative errno on failure.

### `KERNEL_OP_LOG`

Payload:

```
offset  size  field
0x00    u32   level   (0=debug, 1=info, 2=warn, 3=error)
0x04    u32   flags   (reserved, must be 0)
0x08    ...   utf8_bytes[]
```

Response payload: none (`kernel_response_size = 0`).

`kernel_result`: `0` on success; negative errno on failure.

### `KERNEL_OP_STREAM_WRITE`

Payload:

```
offset  size  field
0x00    u32   sid_or_fd
0x04    u32   flags      (reserved, must be 0)
0x08    u32   data_ptr   (guest pointer)
0x0c    u32   data_len   (bytes)
```

Payload length MUST be 16 bytes.

Response payload: none (`kernel_response_size = 0`).

`kernel_result`:

- `>= 0`: number of bytes written (MUST equal `data_len` for full success)
- `< 0`: negative errno (e.g. `-ENOSYS`)

MVP requirement: the microkernel SHOULD support `sid_or_fd` values `1` (stdout)
and `2` (stderr). Other values may return `-ENOSYS` until stream allocation/open
is implemented.

### `KERNEL_OP_STREAM_READ`

Payload:

```
offset  size  field
0x00    u32   sid_or_fd
0x04    u32   max_bytes
```

Response payload: raw bytes read.

`kernel_result`:

- `> 0`: number of bytes read (response size MUST equal this)
- `= 0`: EOF (response size MUST be 0)
- `< 0`: negative errno

In Stage 2 (async baseline), reads that would block SHOULD return `-EWOULDBLOCK`
or remain PENDING until data arrives (implementation choice, must be documented
by the microkernel).

**Implementation note (reference microkernel):**

- For `sid_or_fd == 0` (stdin), empty-but-not-closed reads return:
  - `PENDING` when the microkernel is configured with `asyncStdin: true`, or
  - `DONE` with `kernel_result == -EWOULDBLOCK` when `asyncStdin: false` (Stage 1).
- For `PIPE` streams opened via `KERNEL_OP_STREAM_OPEN(kind=PIPE)`, empty reads
  return `DONE` with `kernel_result == -EWOULDBLOCK` (no PENDING behavior yet).

### `KERNEL_OP_STREAM_OPEN`

Open/allocate a new stream endpoint and return a fresh `sid` scoped to the
current runner.

Payload:

```
offset  size  field
0x00    u32   kind          (endpoint kind; registry below)
0x04    u32   flags         (reserved, must be 0)
0x08    u32   arg_ptr       (guest pointer to kind-specific bytes; optional)
0x0c    u32   arg_len       (bytes; optional)
```

Payload length MUST be 16 bytes.

`arg_ptr/arg_len` is an uninterpreted byte string whose meaning depends on
`kind`. (For example, a future `FILE` kind might treat it as UTF-8 path bytes.)

Response payload: **kind-specific**.

`kernel_result`:

- `>= 3`: the allocated stream id (`sid`)
- `< 0`: negative errno

Initial `kind` registry:

- `0`: `PIPE` (in-memory byte FIFO; `arg_len` MUST be 0)
- `1`: `NAMED_RO` (read-only named byte source; `arg_len` is UTF-8 path/name bytes)

`PIPE` response payload: none (`kernel_response_size = 0`).

`NAMED_RO` response payload (`kernel_response_size = 8`):

```
offset  size  field
0x00    u64   size_bytes
```

If no named source exists for the provided name, the request MUST complete with
`kernel_result == -ENOENT`.

### `KERNEL_OP_STREAM_CLOSE`

Close a previously opened stream.

Payload:

```
offset  size  field
0x00    u32   sid
0x04    u32   flags   (reserved, must be 0)
```

Payload length MUST be 8 bytes.

Response payload: none (`kernel_response_size = 0`).

`kernel_result`:

- `0`: success
- `< 0`: negative errno (e.g. `-EBADF`)

Closing standard streams (SIDs 0/1/2) MUST be a no-op that returns success.

### `KERNEL_OP_TIME_NOW`

Payload: empty (`payloadLen = 0`).

Response payload (`kernel_response_size = 8`):

```
offset  size  field
0x00    u64   unix_ms  (milliseconds since Unix epoch)
```

`kernel_result`: `0` on success; negative errno on failure.

### `KERNEL_OP_COMPILED_MODULES_REFRESH`

Request that the host refresh the compiled module table using the Lisp registry.

Payload:

```
offset  size  field
0x00    u32   registry   (Lisp object pointer to %wasm-compiled-modules%)
0x04    u32   nil        (Lisp object pointer to NIL)
```

Payload length MUST be 8 bytes.

Response payload: none (`kernel_response_size = 0`).

`kernel_result`:

- `>= 0`: number of compiled modules installed
- `< 0`: negative errno (e.g. `-ENOSYS` if unsupported)

### `KERNEL_OP_UI_POLL`

Poll for a batch of UI input events produced by the JS backend/bridge.

Payload (12 bytes):

```
offset  size  field
0x00    u32   max_events   (max event count to return)
0x04    u32   max_bytes    (max response payload size in bytes)
0x08    u32   flags        (bit0: allow_pending_if_empty)
```

Response payload: UI Event Batch (see `doc/wasm/ui-bridge-protocol.md`).

`kernel_result`:

- `>= 0`: number of events encoded in the response payload
- `< 0`: negative errno on failure

If `flags & 0x1` is set and no events are available, the request MAY remain
`PENDING` (Stage 2 semantics). If pending is not supported, return `0` with an
empty response.

### `KERNEL_OP_UI_RENDER`

Submit a UI tree/patch for rendering by the JS backend.

Payload: UI Tree Payload bytes (see `doc/wasm/ui-bridge-protocol.md`).

Response payload: none (`kernel_response_size = 0`).

`kernel_result`:

- `0` on success
- `< 0` negative errno on failure (`-EINVAL` for malformed payload, `-ENOSYS` if UI backend is unavailable)

### `KERNEL_OP_UI_MEASURE_TEXT`

Request text measurement from the JS backend.

Payload (16 bytes):

```
offset  size  field
0x00    u32   font_ptr
0x04    u32   font_len
0x08    u32   text_ptr
0x0C    u32   text_len
```

Response payload (32 bytes):

```
offset  size  field
0x00    f64   width
0x08    f64   height
0x10    f64   ascent
0x18    f64   descent
```

`kernel_result`: `0` on success; negative errno on failure.

## Validation and robustness requirements (host-side)

The microkernel MUST:

- validate `payloadPtr/payloadLen` and `dstPtr/dstLen` bounds against current
  linear memory size,
- validate minimum payload sizes for each opcode,
- impose reasonable request/response size limits (and return `-E2BIG` or similar
  on violations),
- treat malformed payloads as request errors (`kernel_result = -EINVAL`),
- ensure `kernel_drop_request` is idempotent or returns `-EINVAL` on double-drop
  (implementation choice; document it).
