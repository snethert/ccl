# Projected-image READY join — R13: public string-output constructors

This proposal finishes the new-string constructor path before the work moves
to namespace and loader. It executes seven more original definitions through
CCL's public `MAKE-STRING-OUTPUT-STREAM`, native `CLOSE` methods and unchanged
`WITH-OUTPUT-TO-STRING` macro: proposed totals **575 executed / 535 with a
non-NIL witness**, versus the accepted 568 / 531. Admission is not recounted.
This is not an LL15 acceptance submission.

CCL's file compiler compiles `l1-streams.lisp` whole. The constructor, buffer
growth, recycling, close callbacks and method bodies come from that file.
The method reader preserves primary, before and after qualifiers; four GFs
required by close join the existing image (54 total). No C/JS stream service,
replacement writer or replacement close function is added.

The one Lisp source branch replaces the native raw TCR binding-address lookup
in `%STRING-STREAM-IOBLOCK-FREELIST` with `%WASM-THREAD-LOCAL-VALUE`. The backend
uses its existing checked special-location helper, returns NIL when only the
global value exists, and returns the current dynamic value otherwise. It does
not allocate or expose an address. The witness checks absence despite a global
value, nested bindings including NIL, collection and restoration through THROW.
Wrong arities refuse; a control returning the global fallback must fail.

The native pool is **one data cell, subtag 82** (`library/lispequ.lisp`). Native
GC empties it (`lisp-kernel/x86-gc.c`); the proposed collector does the same,
clearing only the destination and never tracing cached contents. Exact count,
source/root preservation, separately rooted cached objects and both placements
are checked. Count and clearing omissions are rejected. Pools, like streams,
remain transient and are not admitted by the image loader. The existing forty
collector-owner checks run against this build.

The stream witness binds the native standard initial pool for its dynamic
extent. It covers character element types, empty/extracted strings, Unicode,
recycling, simultaneous streams, a different active pool, repeated close,
`:abort`, a pool-clearing GC, closed-stream errors, and macro cleanup on normal
return, THROW and ERROR. At the pool-clearing observation the native oracle
really calls `CCL:GC`; ordinary `CORE-COLLECT` oracle calls remain no-ops. No
promise that a cache survives collection is made. The optional pre-existing
fill-pointer-string form of WITH-OUTPUT-TO-STRING belongs to the unfinished
adjustable-array path and receives no credit here. File/terminal/OS streams
and process-wide standard initial bindings are outside this unit.

Direct calls to an image GF are now admitted by the probe linker only when an
explicit graph input contains that actual native GF in its protocol. Merely
being FBOUNDP on the host is insufficient. The graph, installed bindings and
execution are retained; absent graphs, unmarked vectors, non-GFs and a missing
protocol member have controls. The explicit execution-list rule is unchanged.

R10–R12 are integrated. `compiler.py` starts from those product sources and
adds only the thread-local intrinsic and stream branch. The pool collector is
built separately from the unchanged Lisp compilation session and is bound into
the execution environment. R1–R12 replay from their recorded commits (R12:
`f8180b52`); no historical packet is rewritten. The raw packed-bit byte check
remains in the written Worker.

Reproduce from the commit containing this packet, beside `ccl-evidence`:

```sh
python3 tests/wasm/stage1/ready/packet.py verify \
  ../ccl-evidence/2026-09-24-stage1-ready-join-r13 \
  /private/tmp/ccl-work/codex/ready-r13-review/run
```

The verifier runs the full corpus once, writer and four cold boots (both
placements, moved/unmoved), the existing admission controls, pool controls and
the thread-local control. Native qualification is reused only by the complete
proposal-source identity; its fresh author run and the 17-profile reader proof
are retained. Caches and outputs follow the shared bounded-cache and workspace
lease policy. No slot credit or timing claim is made.

Next work is `S1-NAMESPACE-a` followed by `S1-LOADER-a`. The READY projection
will not gain unrelated GFs or metaclass fields to improve its census. Its
remaining graph edges, replacement attribution and callback dispositions stay
open until the namespace/loader work can discharge them.

The constructor witness covers CHARACTER, CCL::BASE-CHARACTER and STANDARD-CHAR.
Other element-type designators reach the general SUBTYPEP environment, which this
image has not initialized. FIXNUM is retained as an explicit boundary: native
signals a Lisp error and the target refuses with checked 4. This is not credited
as a native-compatible error path. Completing that environment belongs to the
file-loading work, not another projection of native type tables.
Three cleanup helpers execute, but their discarded return values receive no
non-NIL-return credit.
