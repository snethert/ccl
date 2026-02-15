# Stream System Specification

**Status:** Active
**Scope:** Stream model used by the Lisp runtime and implemented by the JavaScript microkernel
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

## Purpose

This document specifies the stream model used by the Lisp runtime and implemented by the JavaScript microkernel.

It defines:
   •   Stream identifiers (SIDs)
   •   Stream ownership
   •   Standard streams
   •   Per-runner stream resolution
   •   Byte-stream semantics as exposed by the kernel_request ABI
   •   Buffering and encoding responsibilities (Lisp-side)
   •   Network-backed stream endpoints
   •   Minimal JS microkernel state required to support streams

This document describes the *conceptual* stream system. The concrete I/O ABI is
defined by `doc/wasm/kernel-request-abi.md:1` (opcodes `STREAM_READ`,
`STREAM_WRITE`, and the `STREAM_OPEN`/`STREAM_CLOSE` lifecycle operations).

⸻

2. Stream Identifiers (SIDs)

All streams are referenced by Stream Identifiers (SIDs).
   •   An SID is an integer.
   •   SIDs are scoped to a single Lisp runner.
   •   The same numeric SID in different runners refers to unrelated streams.
   •   SIDs are never shared or transferred between runners.

⸻

3. Stream Namespace

Each runner has an independent stream namespace:

SID → Stream Endpoint

This mapping is maintained by the JS microkernel.

There is no global stream namespace.

⸻

4. Stream Types

A stream endpoint has a type and directionality.

4.1 Byte Streams

A byte stream transmits octets (0–255).
   •   Read returns up to N octets (possibly fewer), or an end-of-stream condition.
   •   Write accepts a sequence of octets.
   •   No encoding interpretation is performed by the JS microkernel.

Byte streams are required to support:
   •   Compiled code and fasl-like loading formats
   •   Binary file formats
   •   Network protocols
   •   Any Lisp feature expecting binary I/O

4.2 Character Streams

CCL supports “character streams” at the Lisp level, but the kernel_request ABI
does not currently expose a distinct character-stream transport.

In the WASM bring-up baseline, the JS microkernel exposes **byte streams only**.
Any character stream behavior (buffering, newline translation, encoding/decoding,
`READ-CHAR`/`READ-LINE` semantics, etc.) is implemented in Lisp on top of byte
streams.

The microkernel performs no line discipline and does not interpret encodings.

⸻

5. Encoding and Text Conversion

The JS microkernel does not perform Unicode normalization, tokenization, or s-expression parsing.

Text conversion rules are:
   •   The microkernel may expose character streams directly (for UI terminals and similar devices).
   •   The Lisp runtime is responsible for buffering and for mapping between character streams and byte streams when needed.

The system uses UTF-8 as the wire format for text crossing the CL/JS boundary (see decisions.md ADR-0002):
   •   CCL internal: UTF-32 (native character representation)
   •   Wire format: UTF-8 (all strings crossing CL/JS boundary)
   •   JavaScript internal: UTF-16 (native JS string representation)

Character streams carry UTF-8 encoded bytes at the transport level. Lisp-side decoding to CCL's internal UTF-32 representation is layered on top of byte streams, keeping the underlying transport stable.

⸻

6. Standard Streams

6.1 Root Runner

The root Lisp runner is created with the following fixed SIDs:

SID 0 — Standard Input
   •   Readable
   •   Byte stream (conventionally UTF-8 text, but treated as bytes)
   •   Bound to the interactive input device
   •   Unclosable

SID 1 — Standard Output
   •   Writable
   •   Byte stream (conventionally UTF-8 text, but treated as bytes)
   •   Bound to the primary output sink
   •   Unclosable

SID 2 — Standard Error
   •   Writable
   •   Byte stream (conventionally UTF-8 text, but treated as bytes)
   •   Bound to the error output sink
   •   Unclosable

These streams always exist for the root runner.

Closing them is a no-op.

6.2 Non-Root Runners

When a non-root runner resolves a standard stream:
   •   stdin resolves to a fresh input stream
   •   stdout resolves to a fresh output stream
   •   stderr resolves to a fresh error stream

These streams are:
   •   Distinct from the root runner’s streams
   •   Closable
   •   Independently buffered by Lisp

The underlying endpoints may map to the same JS sink as the root streams or to separate sinks. This choice is implementation-defined.

⸻

7. Stream Endpoints

A stream endpoint is an implementation-defined JS object representing a source or sink of bytes or characters.

An endpoint may represent:
   •   Interactive UI input (character)
   •   UI output sink (character)
   •   Pipe or buffered queue (byte and/or character)
   •   File- or blob-backed stream (byte and/or character)
   •   Network-backed stream (byte and/or character)

Endpoints define directionality:
   •   Readable
   •   Writable
   •   Read–write

⸻

8. Network-Backed Streams

The microkernel must support endpoints backed by network transport.

8.1 Network Streams as Byte Streams

Network streams are byte streams by default.
   •   Data is transmitted as octets.
   •   Message boundaries are not implied unless the chosen network transport provides them.

Examples of network endpoint backends include:
   •   WebSocket
   •   WebTransport
   •   Fetch streaming (read-only)
   •   Any other JS-accessible transport

8.2 Optional Framed Message Endpoints

If the microkernel exposes message-based transports (e.g., WebSocket messages), it may provide an endpoint policy:
   •   Framed: reads/writes operate on discrete frames
   •   Unframed: reads/writes operate on a byte stream abstraction

The policy is an endpoint property; Lisp code must not assume message framing unless explicitly requested at open time.

⸻

9. Concurrent Output Semantics

If multiple streams are backed by the same underlying JS sink:
   •   Writes may interleave arbitrarily.
   •   No atomicity or ordering guarantees are provided.
   •   The Lisp runtime performs no synchronization.

Managing output interleaving is the user’s responsibility.

⸻

10. Stream Operations

The JS microkernel must support the following operations per runner (via the
kernel_request ABI):

   •   Allocate a new stream endpoint and assign an SID (`STREAM_OPEN`)
   •   Close an SID (`STREAM_CLOSE`)
   •   Read bytes from an SID (`STREAM_READ`)
   •   Write bytes to an SID (`STREAM_WRITE`)

SIDs 0/1/2 are reserved for standard streams. Stream allocation via
`STREAM_OPEN` returns SIDs >= 3.

Closing behavior:
   •   Closing a normal stream releases the endpoint.
   •   Closing an unclosable stream is a no-op.

10.1 Stream open kinds (initial)

`STREAM_OPEN` uses a **kind** registry to choose endpoint behavior.

   •   `PIPE` — in-memory byte FIFO (arg_len MUST be 0)
   •   `NAMED_RO` — read-only named byte source (arg bytes are UTF-8 name/path)

For `NAMED_RO`, the microkernel resolves the name to a byte source (e.g. an
in-memory registry or a backing store) and returns the stream size in the
response payload as described in `doc/wasm/kernel-request-abi.md:254`.

⸻

11. Read Semantics and Buffering

The microkernel delivers raw bytes. It does not buffer for Lisp semantics beyond
whatever buffering is inherent in the chosen endpoint implementation.

All buffering and parsing is the responsibility of the Lisp runtime.
   •   Byte stream buffering: implemented in Lisp when higher-level operations require it.
   •   Character stream buffering: implemented in Lisp; READ-CHAR, READ-LINE, and READ are layered entirely in Lisp.
   •   Tokenization and s-expression parsing are entirely Lisp-side.

⸻

12. Blocking Behavior

Blocking behavior depends on platform support:
   •   If crossOriginIsolated is true, blocking reads may use shared memory and atomic waits.
   •   Otherwise, reads may return a would-block status or suspend execution asynchronously.

The stream interface must support both behaviors for both byte and character streams.

⸻

13. JS Microkernel Stream Tables

To implement this specification, the JS microkernel must maintain:

Per runner:
   •   A stream table mapping SID → endpoint
   •   A record of unclosable SIDs (root runner only)

Per endpoint:
   •   Stream type: byte or character
   •   Directionality
   •   Backend kind: UI, pipe, file/blob, network
   •   Open/closed state
   •   Backend configuration (for network: transport handle and framing mode)

No other global stream state is required.

⸻

14. Guarantees
   •   Streams are per-runner.
   •   Standard streams are resolved per-runner.
   •   Root standard streams are unclosable.
   •   Both byte streams and character streams exist.
   •   Lisp owns all buffering and parsing.
   •   Output interleaving is permitted and unmanaged.
   •   The microkernel does not interpret stream contents beyond unit type (octet vs character).

⸻

15. Lisp Stream Classes and Required Shims

This specification defines the host-level stream interface (SIDs, endpoints, and unit I/O). It is deliberately lower-level than Lisp’s stream class hierarchy.

15.1 Basic vs. Fundamental Streams

Concepts such as “basic streams” or “fundamental streams” are Lisp implementation details. The microkernel does not know about them and does not provide APIs for them. Lisp stream classes should be implemented entirely in the runtime, layered on top of this spec’s SID-based I/O.

Implication:
   •   The concept of a “basic stream” exists only in Lisp, not in the microkernel.
   •   The microkernel exposes only byte/character units and endpoint properties.

15.2 Minimum Shims for Lisp Runtimes

A Lisp runtime that expects specialized stream classes typically needs the following shims:
   •   SID-backed stream subclass: a Lisp class that stores SID and stream metadata (type, direction).
   •   Read/write methods: Lisp methods that call into the microkernel to read/write one unit, then layer buffering as needed.
   •   Buffering mixins: Lisp-side byte/character buffers that implement READ-CHAR, READ-LINE, READ-SEQUENCE, WRITE-STRING, etc.
   •   End-of-stream handling: Lisp-side EOF conditions and policy decisions (e.g., eof-error-p).
   •   Close semantics: Lisp-side close method that calls the microkernel close operation and marks the stream as closed.

15.3 What Lisp Defers to the Host

The Lisp runtime defers only the following to the host:
   •   Allocation and ownership of stream endpoints (SID creation).
   •   The ability to read or write a single unit (octet or character) from/to an endpoint.
   •   Whether a stream is readable, writable, or closed.
   •   Network transport details (for network-backed endpoints).

All higher-level behavior—including buffering, character encoding, tokenization, and stream class hierarchy—is the responsibility of Lisp.
