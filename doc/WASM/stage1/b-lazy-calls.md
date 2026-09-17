# Lazy installation of generated B entries — 16 September 2026

The [loader and paired stubs](../../../tests/wasm/stage1/b-lazy-calls/README.md)
install reviewed compiler-generated B functions on first use. A private catalog
binds each code ID and version to its slot, module digest, import inventory,
profile and public/internal export roles. The actual bytes and signatures are
checked before instantiation. Start functions, segments and other initialization
authority are refused. Both table entries are prepared before publication;
installation never writes Lisp memory. Authentication is against the trusted
Worker owner's catalog, not a signature from an external publisher.

Public and tail stubs preserve SELF, argument count and continuation and forward
with real Wasm tail instructions. The generated callee retains its arity and
binding checks. Installation failure is retryable; a held stub works after the
pair is installed. The loader also checks the existing registry and table
identities, refuses reentrancy and snapshots admitted descriptors and imports.
A failure inside a generated caller restores its original arguments, output
reservation, roots and result count before retry.

The catalog covers 270 modules; 267 are actually installed during the corpus.
There are 2,870 cold installations in each observation mode. All 2,964 target
comparisons and 36 chains of 100,000 steps in a 2 KiB stack reproduce the reviewed
eager result exactly, including allocation and root checks. Thirty-five further
installation cases comprise five successes and thirty refusals. Fourteen loader
and stub mutants fail at their recorded assertions. Original development
failures are retained. The first replay’s temporary-directory cleanup removed
its inner log; the root failure log, exact scripts and a reproduction of the
macOS path-alias cause remain. The verifier now retains failed work directories.

This changes no compiler or upstream kernel source. The unchanged modules,
native oracle and R6/R6a evidence are pinned to the accepted tail-call packet;
no fresh native build or native execution is claimed. The retained verifier
replays installation, the entire target corpus, malformed-module controls and
all mutants from committed sources.

The user approved this auxiliary unit after Claude’s seventy-third audit. Its
three runtime files are integrated byte-for-byte under `runtime/wasm32`, with
no LL05 slot credit.
The loader is synchronous and local to one Node Worker; browser installation
is not qualified by this packet. Collection, concurrent
publication, asynchronous fetch, production image loading and profile
materialization remain separate work. Errors still use checked Wasm exceptions;
the full Lisp condition path and dynamic cleanup/binding extent remain open.
The next implementation work is the condition path.

Packet: `ccl-evidence/2026-09-16-stage1-b-lazy-calls-r1`.

Historical replay: this packet’s runner checks the then-current shared tail-call
backend. Replay it at `6ccdf05d`; the direct-context packet separately qualifies
the unchanged loader against the newer binaries. Integration does not rewrite
that historical producer or its retained pins.
