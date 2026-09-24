# Bridge admission and publication

Client directed cases in `controls.mjs` distinguish argument span/alignment,
stack ownership, incoming-frame identity, RUNNING state, no outstanding request,
fixnum opcode/descriptor/count, operation range, object tag/header/data span,
vector kind, owned heap extent, count sign/capacity, seek origin, path kind,
scalar validity and UTF-8 bound. Buffer ownership is active-heap-only; strings
may additionally be in declared pinned image regions. Object starts are
supplied by the trusted generated Lisp/owner, as for the accepted arithmetic
services; this leaf is not a heap validator or memory sandbox.

Completion cases distinguish generation, outcome, active state, payload extent,
fixnum result range, count/length equality, requested extent, and no data on
error. Every failed completion leaves the buffer unchanged and restores the
TCR. The full generated check additionally checks six argument failures through
the B call path, before any host request, and all 64 TCR words after the unwind.

The host independently checks lifetime, generation and active state before any
operation. Its final generation/active recheck protects completion publication.
The host is synchronous and is the sole completion writer in this profile; the
CAS race throw is an invariant assertion, not a second supported race outcome.
The Worker cannot change a request while waiting. The bounded fixed request
span is admitted by the memory owner. A nested call and generation exhaustion
are defensive refusals: the profile permits one call stack and fewer than
2^32 requests per Worker lifetime. A new lifetime must be created before that
limit; the descriptor generation must never wrap. No claim of multi-Worker
scheduling or cancellation is made.

Provider limits, paths, handle lifecycle and manifest admission were exercised
in the parent namespace packet. Here the host's seek-result bound has its own
successful-limit/overflow/negative/invalid-origin cases, preserving position.
The full trace observes stale handles, independent positions, EOF and all
read-only policy returns. Faults remove the post-GC buffer reload, buffer copy,
correct EOF count and FOREIGN publication; each fails at its named observation.
The 8,128-byte response cap has an oversized request against a 9,000-byte file;
native and bounded outcomes are retained separately, with unwritten-tail and
position assertions. Omitting the cap is a fifth rejected fault.

The adapter preserves the accepted symbol leaf's fixed/dynamic B result
selection and capacity checks, specialized to one value and four arguments.
Publication happens after the synchronous import returns and cannot safepoint.
No heap address from before that import is used to locate the read buffer.
