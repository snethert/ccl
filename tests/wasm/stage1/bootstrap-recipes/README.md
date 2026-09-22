# Recipes for the closed-definition cohort

**458 original definitions execute (+22), 427 with non-NIL witnesses (+20).**
This packet works through the 64 names left by bootstrap-closure. The compiler,
runtime and CCL source are unchanged; native R6/R6a is reused by the exact final
source hashes from that packet. Execution counts and every cohort disposition
are retained in `summary.json` and `recipe-cohort.json`. There are 16,340 target
comparisons, including 14,992 exact native comparisons; the inherited numerical
differences remain separately counted. The requested cohort contributes 21 new
executions, and whole-file compilation adds NEED-USE-EQL as the twenty-second.
Admission remains 1,993 of 2,231 parsed definitions, with 44 of 57 files complete.
The file compiler records 76 admitted l0-hash records out of 95, including
anonymous compile-time records; refusals remain explicit.

New recipes exercise original array metadata and indexing functions, string
stream reads and writes, symbol restoration and unbinding, detached thread
initialization, hash counters, dispatch-table clearing and probing, a real
TOPLEVEL transfer, and invocation of the function returned by
MAKE-NUMERIC-CTYPE-PREDICATE. That closure is called after a collecting poll.

`observers.lisp` contains callers for results that cannot be compared as raw
addresses or architecture tags. Each caller declares the original function
NOTINLINE; compilation must retain that named dependency. The array observers
compare the returned subtype with the actual backing vector's typecode, or
read the simple-array flag after the setter. The index caller retains its real
CCL &LEXPR frame and consumes the result before returning. These are callers,
not replacements or source rewrites of the original definitions. Input and
global post-state are compared as well as returned values, at both placements
before and after collection.

The hash counter recipes use the native constructor's populated backing vector,
with the GC link, flags, count epoch and back-pointer detached for transport.
They retain all fourteen prefix fields and all key/value slots. A full-sized
HASH-TABLE wrapper supplies the backing vector; native process locks and
callables are outside these two readers' scope. Deleted counts straddle each
rehash threshold. Dispatch recipes cover empty, occupied, full and obsolete
wrapper cases for insertion of a new wrapper; existing-key identity matching
is not claimed by those rows.

The new marker recipe exposed a real compilation-environment gap:
INVALID-HASH-KEY-P compiled alone treated its file-local symbol macros as
special-variable reads and returned NIL for an empty-slot marker. CCL's own
file compiler now processes `l0-hash.lisp`, including its compile-time forms.
Every refused definition in that file is retained by name; no whole-file
admission claim is made. The original standalone output is retained as a
control and must fail the marker recipe. No special-case body replaces the
CCL definition. NEED-USE-EQL also becomes executable through that environment;
its inputs use the shared boxed-number domain, excluding the native/target
single-float and fixnum representation differences.

The requested 64 includes seven fixture/primitive names and the target's own
%SLOT-REF entry. Thirteen destructive single-float names have only non-destructive
counterparts in the native 64-bit image; their equivalent-value coverage is
already in the libm packet and is not new exact-original execution credit.
Native dynamic-library and exception-context interfaces remain excluded.
Other rows name the necessary lowering, graph transport, live-frame oracle,
function-cell state or architecture-specific comparison. A NIL pool, all-zero
random state, out-of-range Unicode character or zero-only hash input does not
close those obligations.

```sh
python3 tests/wasm/stage1/bootstrap-recipes/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-recipes-r1 \
  --output /tmp/bootstrap-recipes-replay
```

The verifier rebuilds and executes the generated corpus, replays the eight
controls and trap-mode control, and compares all deterministic output. It
reuses the unchanged compiler's native qualification by hash. Original
failed development attempts are retained. This proposal is not integrated and
carries no LL15 slot credit.
