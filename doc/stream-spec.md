# Streams Spec (CCL Port-Friendly)

This specifies the Lisp-visible stream abstraction and the host I/O interface supporting cooperative blocking for reads and writes. Streams are byte/character conduits only (not object/message streams, not control-plane IPC).

This version is updated to ease porting fd-based Lisp runtimes (including CCL) while retaining capability-backed endpoints. It explicitly allows an fd-compatibility layer, external formats metadata, and standard-stream provisioning hooks.

## Goals
- Lisp code experiences regular blocking streams.
- Blocking is implemented by cooperative suspension of a runner, not OS threads.
- Streams are capability-backed endpoints managed by the host.
- ASCII-only character semantics initially, with a forward path to UTF-8.
- Compatibility path for fd-based runtimes without requiring POSIX compliance.

## Non-goals
- POSIX fd compatibility (full POSIX semantics are not required).
- “Object streams” / transparent cross-process Lisp object transport.
- Fair scheduling guarantees or starvation avoidance policy.

---

## 1. Conceptual model

A stream is a Lisp object representing a half-duplex or full-duplex endpoint. Each stream object wraps an opaque stream capability (`sid`) minted by the host.

A stream endpoint may represent:
- console input/output
- UI terminal pane
- file-like object
- socket-like object
- pipe between runners
- log sink

The host owns the actual endpoint; the Lisp side owns buffering and the standard stream API.

---

## 2. Stream identity and capabilities

### Stream IDs
- `sid` is an opaque integer/capability token.
- Only the host can create/validate `sid`.
- A `sid` is valid only within the host instance that minted it.

### Access control
- A runner may use a `sid` only if the host granted it to that runner (directly at spawn or via a passed capability).
- The Lisp runtime treats `sid` as unforgeable.

---

## 3. Stream types and modes

### Modes

A stream has a bitmask mode:
- INPUT (readable)
- OUTPUT (writable)
- BINARY (byte operations supported)
- CHAR (character operations supported)
- INTERACTIVE (affects buffering policy; e.g., line buffering)

A stream may be both INPUT|OUTPUT (bidirectional).

### Lisp-visible stream classes

Minimum set:
- binary-input-stream
- binary-output-stream
- character-input-stream
- character-output-stream
- two-way-stream (optional: a pair of input/output streams)

You can implement these as a single class with flags; this spec is semantic.

### Compatibility note (fd-based runtimes)

Lisp runtimes MAY expose multiple stream class families (e.g., “basic” vs “fundamental”, binary vs character, file vs socket). This spec does not restrict such class hierarchies; it only defines the required behavior for the stream API.

---

## 4. Required host interface

The host provides these syscalls/imports to each runner. All functions are synchronous from the runner’s point of view, but may cause the runner to cooperatively suspend via wait_*.

### 4.1 Constants

Return codes (integers):
- OK (not used directly; success is n >= 0)
- WOULD_BLOCK = -1
- EOF = -2
- ERR = -3 (generic error; extended via errcode)

### 4.2 Read/Write primitives

`io_read(sid, dst_ptr, max_bytes) -> n | WOULD_BLOCK | EOF | ERR`
- If n > 0: wrote n bytes into linear memory at dst_ptr.
- If WOULD_BLOCK: endpoint currently has no data available without blocking.
- If EOF: endpoint is closed for reading.
- If ERR: a host error occurred; see io_last_error.

`io_write(sid, src_ptr, nbytes) -> n | WOULD_BLOCK | ERR`
- If n > 0: consumed n bytes from src_ptr.
- Partial writes are allowed and expected.
- If WOULD_BLOCK: cannot accept data without blocking (bounded buffer full).
- If ERR: host error occurred.

### 4.3 Cooperative wait primitives

These suspend the current runner until the condition holds, then return.

`io_wait_readable(sid) -> 0 | ERR`
- Returns when a subsequent io_read is expected to return n > 0 or EOF or ERR.
- Spurious wakeups permitted; caller must retry io_read.

`io_wait_writable(sid) -> 0 | ERR`
- Returns when a subsequent io_write is expected to write at least 1 byte or return ERR.
- Spurious wakeups permitted; caller must retry io_write.

### 4.4 Optional primitives

`io_flush(sid) -> 0 | WOULD_BLOCK | ERR`
- Flushes host-side buffers for stream if meaningful.
- If WOULD_BLOCK, caller should io_wait_writable then retry.

`io_close(sid) -> 0 | ERR`
- Closes endpoint (direction per host semantics; ideally full close).

`io_poll(sid, mask) -> ready_mask | ERR` (optional)
- mask: bits for readable/writable.
- Allows implementing listen/peek efficiently without blocking.

`io_last_error() -> errcode`
- Returns last error code for current runner thread of execution (host-defined).

---

## 5. Lisp-side blocking semantics

All Lisp stream operations must appear blocking in the usual way. Internally they are implemented as “try; if WOULD_BLOCK then wait; retry”.

### 5.1 Binary read contract

A binary read operation (e.g., read-byte, read-sequence) obeys:
- If data is available, return promptly with some data.
- If no data is available:
  - block (cooperatively) until data arrives or EOF.
- EOF behavior must match CL norms:
  - if EOF is allowed, return EOF marker / shorter count
  - otherwise signal an end-of-file condition

### 5.2 Binary write contract

A binary write operation (e.g., write-byte, write-sequence) obeys:
- Must not drop bytes.
- If the sink cannot accept data:
  - block (cooperatively) until it can, then continue.
- Partial writes are hidden from callers by looping until completion, except where CL allows partial completion (e.g., some write-sequence variants); choose a consistent policy and document it.

### 5.3 Character operations

Character streams are defined as operations over bytes with an encoding.

Initial encoding for CHAR streams:
- ASCII only: each character is one byte 0–127.
- Bytes outside 0–127 are an error unless explicitly allowed as “raw”.

Character operations must be implemented using internal byte buffers plus the binary primitives.

---

## 6. Buffering rules

Each stream maintains Lisp-side buffers.

### 6.1 Input buffer

Fields:
- in_buf (byte vector)
- in_pos, in_len
- unread_slot (optional single-char pushback)

Refill procedure (blocking):
1. If in_pos < in_len, data exists.
2. Else call io_read.
3. If WOULD_BLOCK, call io_wait_readable then retry.
4. If EOF, mark stream EOF.

### 6.2 Output buffer

Fields:
- out_buf (byte vector)
- out_len
- line_buffered boolean (for interactive streams)

Drain procedure (blocking):
1. While bytes remain to write:
  - call io_write.
  - if WOULD_BLOCK, io_wait_writable then retry.
  - if partial write, advance pointer and continue.

Flush triggers:
- finish-output: must drain fully (blocking).
- force-output: may drain partially but should attempt to push out buffered bytes; may block if you choose strict semantics.
- For INTERACTIVE or line_buffered: flush on newline byte.

### 6.3 Default buffer sizing

Implementation choice, but recommended:
- input buffer: 4–32 KB
- output buffer: 4–32 KB
- for interactive output: line buffering + modest block buffer

### 6.4 Auto-flush (optional)

Runtimes may designate streams for periodic or interactive auto-flushing. This is compatible with Common Lisp systems that automatically force output on certain streams (e.g., terminal output).

---

## 7. Standard stream variables

The runtime must supply the usual CL dynamic variables, bound to stream objects:
- *standard-input* : character input (ASCII)
- *standard-output*: character output (ASCII)
- *error-output*   : character output (ASCII), unbuffered or line-buffered
- *terminal-io*    : bidirectional character stream (optional but recommended)
- *query-io*       : bidirectional character stream (optional but recommended)
- *debug-io*       : output stream for debugger (optional)

Host provides these at runner spawn time via initial capabilities.

Per-runner defaults are recommended (stdout/stderr isolation).

### Standard stream provisioning hook

The host MUST provide initial stream capabilities and MAY provide a runtime-specific hook for constructing standard streams. This allows fd-based or capability-based runtimes to bind standard streams without rewriting their initialization logic.

---

## 8. External formats and encodings

Each stream may have an external format (encoding + line termination). ASCII is the required minimum; other encodings may be declared but unimplemented.

Runtimes SHOULD expose external-format metadata to Lisp (for compatibility with existing stream APIs), even if only ASCII is supported initially.

---

## 9. Error model and conditions

Host errors (ERR) map to Lisp conditions:
- stream-error for I/O failures.
- end-of-file for EOF where not permitted.
- type-error or stream-error for encoding violations (non-ASCII in CHAR stream).

Restart behavior is optional initially, but recommended minimal restarts:
- retry (re-attempt operation)
- abort (propagate / unwind)
- use-value (for read-char EOF-value cases, if you support it)

---

## 10. Required stream operations

This section specifies required behavior; names are descriptive and can map to your internal runtime functions.

### 10.1 Binary primitives
- read-bytes(stream, dst, start, end) -> count | eof
  - Blocks until at least 1 byte is read, EOF, or error.
- write-bytes(stream, src, start, end) -> count
  - Blocks until all requested bytes written, or error.
- finish-output(stream) drains output buffer; may block.
- force-output(stream) attempts flush per your semantics; may block.
- clear-input(stream) discards buffered input; may optionally drain host input.
- clear-output(stream) clears Lisp-side output buffer (does not guarantee host flush).

### 10.2 Character primitives (ASCII)
- read-char(stream, eof-error-p, eof-value) -> char | eof-value
  - Blocks until char or EOF.
- unread-char(char, stream) supported for last-read char; may be 1-char pushback only.
- peek-char(stream, ...) may block or may consult buffer first; document policy.
- read-line(stream, eof-error-p, eof-value) -> string, true/false
  - Blocks and returns a line without newline, plus flag for whether newline was present.
- write-char(char, stream) writes ASCII char; blocks on flush as needed.
- write-string(string, stream, start, end) writes; blocks as needed.

### 10.3 listen
- If input buffer has data, listen returns true.
- If buffer empty:
  - either return false conservatively, or
  - use io_poll/nonblocking io_read attempt to detect readiness without blocking.
This must be explicitly chosen and documented.

---

## 11. EOF and close semantics

### EOF
- Once EOF is observed on input, subsequent reads return EOF immediately (or signal as appropriate).
- EOF is per-direction; bidirectional streams may close read while write still works.

### Close
- close should call io_close(sid) if supported.
- If host close is not supported, mark the stream closed in Lisp and make further operations signal stream-error.

---

## 12. Compatibility: fd-style runtimes

This spec is capability-first, but fd-based Lisp runtimes can be supported by an optional compatibility layer.

### 12.1 fd compatibility layer (optional)

The host MAY expose a minimal fd-like compatibility API:
- A mapping from sid -> integer fd token.
- An fd token can be passed to legacy stream backends that expect a small integer identity.
- No POSIX semantics are required beyond the ability to read, write, wait, and close.

This enables reuse of fd-oriented stream classes without rewriting the runtime’s core stream machinery.

### 12.2 Timeouts and deadlines (optional)

The host MAY expose per-stream input/output timeouts or deadlines. Runtimes that already expose these features may map them to host capabilities.

---

## 13. Forward compatibility: UTF-8 path

To avoid trapping yourself in ASCII-only design:
- Keep CHAR streams defined as “bytes + codec,” where codec is currently ASCII.
- Store strings internally as a distinct string type decoupled from stream bytes.
- When adding UTF-8:
  - input: decode sequences from byte buffer to codepoints
  - output: encode codepoints to UTF-8 bytes
  - invalid sequences signal stream-error or replacement policy (choose explicitly)

Nothing in this spec requires changing the host primitives for UTF-8; only Lisp-side codec changes.

---

## 14. Separation from control-plane IPC

Streams are for byte/char I/O only.

Do not overload streams for:
- job dispatch
- module loading requests
- synchronization
- structured message passing

Those use a separate IPC mechanism (mailboxes/capabilities) with its own blocking semantics.

---

## 15. Minimal compliance checklist

A runtime is compliant with this spec if it provides:
- Host: io_read, io_write, io_wait_readable, io_wait_writable with the return semantics above.
- Lisp: blocking read-char, write-char, read-byte, write-byte, read-line, write-string, finish-output.
- ASCII-only CHAR streams with explicit error on non-ASCII.
- Per-runner standard stream variables bound to host-provided stream capabilities.
- External-format metadata exposed to Lisp (ASCII required; others optional).

This is enough to run a large amount of ordinary CL-style I/O code without POSIX.
