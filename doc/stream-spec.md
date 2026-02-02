Stream System Specification

1. Scope

This document specifies the stream model used by the Lisp runtime and implemented by the JavaScript microkernel.

It defines:
   •   Stream identifiers (SIDs)
   •   Stream ownership
   •   Standard streams
   •   Per-runner stream resolution
   •   Byte and character stream semantics
   •   Buffering and encoding responsibilities
   •   Network-backed stream endpoints
   •   Minimal JS microkernel state required to support streams

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
   •   Read returns a single octet or an end-of-stream condition.
   •   Write accepts a single octet.
   •   No encoding interpretation is performed by the JS microkernel.

Byte streams are required to support:
   •   Compiled code and fasl-like loading formats
   •   Binary file formats
   •   Network protocols
   •   Any Lisp feature expecting binary I/O

4.2 Character Streams

A character stream transmits character units.
   •   Read returns a single character unit or an end-of-stream condition.
   •   Write accepts a single character unit.
   •   Character units are implementation-defined but must be consistent within a stream.

The microkernel performs no line discipline.

4.3 Additional Stream Types

The Lisp runtime may expose higher-level stream types built on byte or character endpoints:
   •   Two-way streams (paired input/output endpoints)
   •   Echoing streams (input echoed to an output endpoint)
   •   Broadcast streams (writes fan out to multiple output endpoints)
   •   Concatenated streams (reads pull sequentially from multiple input endpoints)
   •   Synonym streams (indirect references to dynamically bound streams)

These are Lisp-level compositions and do not require special microkernel support beyond the base stream operations.

⸻

5. Encoding and Text Conversion

The JS microkernel does not perform Unicode normalization, tokenization, or s-expression parsing.

Text conversion rules are:
   •   The microkernel may expose character streams directly (for UI terminals and similar devices).
   •   The Lisp runtime is responsible for buffering and for mapping between character streams and byte streams when needed.

Character encoding is an endpoint policy and may be declared without being supported by the Lisp runtime. The microkernel does not validate or transform character encodings; it only delivers character units or octets as defined by the endpoint.

Future UTF-8 support, if added, must be layered as:
   •   A byte stream carrying UTF-8 bytes
   •   Lisp-side decoding into a character stream abstraction
so that the underlying transport remains stable.

⸻

6. Standard Streams

6.1 Root Runner

The root Lisp runner is created with the following fixed SIDs:

SID 0 — Standard Input
   •   Readable
   •   Character stream
   •   Bound to the interactive input device
   •   Unclosable

SID 1 — Standard Output
   •   Writable
   •   Character stream
   •   Bound to the primary output sink
   •   Unclosable

SID 2 — Standard Error
   •   Writable
   •   Character stream
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

The JS microkernel must support the following operations per runner:
   •   Allocate a new stream endpoint and assign an SID
   •   Query endpoint properties (type, direction, open/closed)
   •   Read one unit from an SID (octet for byte streams; character unit for character streams)
   •   Write one unit to an SID (octet for byte streams; character unit for character streams)
   •   Close an SID

Closing behavior:
   •   Closing a normal stream releases the endpoint.
   •   Closing an unclosable stream is a no-op.

⸻

11. Read Semantics and Buffering

The microkernel delivers single units (octet or character unit). It does not buffer for Lisp semantics.

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

14. SID Shim Behavior (fd masquerade)

SIDs are designed to masquerade as file descriptors for Lisp’s purposes.
   •   Lisp may treat SIDs as fd-like integers.
   •   The microkernel does not implement a full POSIX stack.
   •   Only the stream operations defined in this spec are required.

This shim behavior exists solely to keep fd-oriented Lisp code working without emulating POSIX file descriptors beyond stream I/O semantics.

⸻

15. Guarantees
   •   Streams are per-runner.
   •   Standard streams are resolved per-runner.
   •   Root standard streams are unclosable.
   •   Both byte streams and character streams exist.
   •   Lisp owns all buffering and parsing.
   •   Output interleaving is permitted and unmanaged.
   •   The microkernel does not interpret stream contents beyond unit type (octet vs character).
