# Kernel Request ABI (WASM Imports)

**Status:** Draft (replacement-track shared-memory-first hot paths)

## Scope

This document defines the **guest↔host ABI** used by a WASM runner (the Lisp
kernel/runtime) to request external services from the JavaScript microkernel.

It specifies:

- the required WASM imports and their semantics,
- request lifecycle and error conventions,
- replacement-track shared-memory transport requirements for hot-path classes,
- compatibility copy-response behavior for bootstrap/control/diagnostics lanes,
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

### Optional import (compatibility optimization)

- `kernel_wait(requestId: u32, deadlineMs: i32) -> status: u32`

`deadlineMs` conventions (if implemented):

- `-1`: wait indefinitely
- `0`: do not block (equivalent to `kernel_poll`)
- `>0`: wait up to `deadlineMs` milliseconds

### Replacement-track transport contract (normative)

For replacement-track runtime lanes:

- Hot-path runtime/kernel/storage/UI classes MUST use shared-memory channel
  transport contracts (`shared_ring_v1`) defined by
  `doc/wasm/tickets/RPL-03-shared-memory-ipc-core.md`.
- Copy/message request/response paths are compatibility-only and MUST be
  limited to bootstrap, control, diagnostics, and explicitly labeled legacy
  lanes.
- Routing a required hot-path class through copy/message transport is a
  contract violation and MUST fail startup-gate validation (`SRG-08`).

### External-call imports (WASM FFI, MVP)

WASM `external-call` forms are lowered to **direct WASM imports** from the
module namespace `ccl` (the same namespace as `kernel_request`).

- **Import name:** the literal external name string passed to `external-call`.
- **Signature:** all parameters and the result are `i32`.
- **Supported arities:** 0, 1, 2, 3, 4, 5, 7 parameters (current compiler support).
- **Supported argument types:** `:address`, `:signed/unsigned-fullword`,
  `:signed/unsigned-halfword`, `:signed/unsigned-byte`.
- **Supported result types:** `:void` or integer types listed above.
- **Unsupported:** `:address` results, floats, structs, callbacks, or varargs.

Pointer arguments are 32‑bit linear‑memory offsets. Callers are responsible for
passing valid pointers and lengths. Unsupported types or arities are compile‑time
errors in the WASM backend.

## Interrupt ABI (host-side flags)

Interrupt delivery is **cooperative** in the secure replacement runtime model.
There is no
`kernel_request` opcode for interrupts in the MVP. Instead:

- The host requests an interrupt by **setting the runner's interrupt_pending flag**
  in the TCR (or equivalent runtime structure in linear memory).
- The runner **polls at safepoints** and at explicit stepping boundaries
  (`wasm_ccl_step`) to deliver the interrupt.

This keeps interrupt delivery deterministic at safepoints without introducing
fallback transport semantics. A future extension may add an explicit
`KERNEL_OP_INTERRUPT` opcode, but it is not required for MVP.

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

## Response payload (copy path for compatibility lanes)

The microkernel may associate an optional response byte buffer with each
request. For replacement-track lanes, this copy path is compatibility-only for
bootstrap/control/diagnostics operations; hot-path classes MUST use shared
channel transport. The guest obtains copy-path responses by:

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

### Shared-channel and direct-write response evolution (TODO)

Replacement-track hot paths are shared-channel-first and do not rely on
`kernel_copy_response` as their normative response mechanism.

TODO(zero-copy): Provide optional ABI extensions that avoid this copy by writing
responses directly into guest linear memory (caller-provided output buffers or a
shared arena/ring buffer). Any zero-copy form MUST define explicit lifetime and
invalidation rules. Copy-path behavior remains required only for compatibility
lanes (bootstrap/control/diagnostics and explicit legacy paths).

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
- `KERNEL_OP_FS_PROBE     = 0x0000_0008`
- `KERNEL_OP_FS_TRUENAME  = 0x0000_0009`
- `KERNEL_OP_FS_DIRECTORY = 0x0000_000A`
- `KERNEL_OP_FS_FILE_WRITE_DATE = 0x0000_000B`
- `KERNEL_OP_FS_RENAME    = 0x0000_000C`
- `KERNEL_OP_FS_DELETE    = 0x0000_000D`
- `KERNEL_OP_FS_ENSURE_DIRS = 0x0000_000E`
- `KERNEL_OP_FS_DELETE_EMPTY_DIR = 0x0000_000F`
- `KERNEL_OP_FS_DELETE_TREE = 0x0000_0010`
- `KERNEL_OP_STREAM_SEEK  = 0x0000_0011`
- `KERNEL_OP_STREAM_TRUNCATE = 0x0000_0012`
- `KERNEL_OP_UI_POLL      = 0x0000_0020`
- `KERNEL_OP_UI_RENDER    = 0x0000_0021`
- `KERNEL_OP_UI_MEASURE_TEXT = 0x0000_0022`
- `KERNEL_OP_RUNTIME_EVENT = 0x0000_0023`
- `KERNEL_OP_RUNTIME_COMMAND_POLL = 0x0000_0024`

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
- `2`: `FILE` (persistence service file; `arg_len` points to file-open payload, see `doc/wasm/persistence-service-spec.md`)

`PIPE` response payload: none (`kernel_response_size = 0`).

`NAMED_RO` response payload (`kernel_response_size = 8`):

```
offset  size  field
0x00    u64   size_bytes
```

If no named source exists for the provided name, the request MUST complete with
`kernel_result == -ENOENT`.

`FILE` response payload: none (`kernel_response_size = 0`).

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

### `KERNEL_OP_STREAM_SEEK`

Seek to a new position within a stream.

Payload:

```
offset  size  field
0x00    u32   sid
0x04    u32   whence   (0=SEEK_SET, 1=SEEK_CUR, 2=SEEK_END)
0x08    i64   offset
```

Payload length MUST be 16 bytes.

Response payload (`kernel_response_size = 8`):

```
offset  size  field
0x00    u64   new_position
```

`kernel_result`:

- `0`: success
- `< 0`: negative errno (e.g. `-EINVAL`, `-EBADF`, `-ENOSYS`)

`STREAM_SEEK` is required for `FILE` streams; other stream kinds may return
`-ENOSYS` or `-EBADF`.

### `KERNEL_OP_STREAM_TRUNCATE`

Resize a file-backed stream to a new length.

Payload:

```
offset  size  field
0x00    u32   sid
0x04    u32   flags   (reserved, must be 0)
0x08    u64   length
```

Payload length MUST be 16 bytes.

Response payload: none (`kernel_response_size = 0`).

`kernel_result`:

- `0`: success
- `< 0`: negative errno (e.g. `-EINVAL`, `-EBADF`, `-ENOSYS`)

`STREAM_TRUNCATE` is required for `FILE` streams; other stream kinds may return
`-ENOSYS` or `-EBADF`.

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

### `KERNEL_OP_RUNTIME_EVENT`

Submit a runtime bridge message for UI integration.

Payload: UTF-8 JSON bytes for a runtime bridge envelope (see `doc/wasm/runtime-bridge.md`).

Response payload: none (`kernel_response_size = 0`).

`kernel_result`:

- `0` on success
- `< 0` negative errno on failure (`-EINVAL` for malformed JSON, `-ENOSYS` if runtime bridge is unavailable)

### `KERNEL_OP_RUNTIME_COMMAND_POLL`

Poll for pending runtime `command.invoke` requests destined for the Lisp runtime.

Payload (8 bytes):

```
offset  size  field
0x00    u32   max_bytes
0x04    u32   flags      (bit0: allow_pending_if_empty)
```

Response payload: Runtime Command Frame bytes.

Frame layout:

```
offset  size  field
0x00    u32   frame_version  (currently 1)
0x04    u32   invocation_id_len
0x08    u32   command_id_len
0x0c    u32   args_form_len
0x10    u32   context_form_len
0x14    u32   reserved       (0)
0x18    ...   invocation_id_utf8
...            command_id_utf8
...            args_form_utf8
...            context_form_utf8
```

`args_form_utf8` and `context_form_utf8` are Lisp-readable forms produced by the host adapter.

`kernel_result`:

- `1` when a command frame is returned
- `0` when no command is available
- `< 0` negative errno on failure (`-E2BIG` when `max_bytes` is too small, `-EINVAL` for malformed payload)

If `flags & 0x1` is set and no command is available, the request MAY remain
`PENDING` (same pending semantics as `KERNEL_OP_UI_POLL`).

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
