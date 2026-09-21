# Portable startup statistics: audit 131 follow-up

This auxiliary proposal closes the four findings in audit 131. No compiler,
shared runtime, original fixture or accepted result changes. No LL15 credit.
The parent packet and all 88 parent source pins remain immutable.

The signed D1 decoder and six added native GCTIME inputs exercise sign-padding
at 2^31, 3,000,000,000 and 2^63 microseconds and adjacent boundaries. Omitting
the sign pad now fails a native-value comparison. Seven directed runtime
refusals isolate each admission predicate and assert no state change; six
previously unisolated predicates each have a remove-one-check control.

An unavailable owner clock publishes a NIL snapshot. Generated Lisp signals
an explicit owner-provided SIMPLE-ERROR instance instead of allowing a host
exception to escape. Both backwards and throwing clocks run through ordinary
and named generated calls, HANDLER-CASE and UNWIND-PROTECT at both placements.
Handlers return 701 and observe cleanup 611; binding chains, root chains and
stack state restore. This is a new owner-error contract, not a claim that
native GCTIME has a failing browser clock. The condition image uses the accepted
twelve-row condition layout; this fixture is not a production condition factory.

The five browser-config effects remain accepted only for the browser provider.
Node replay of browser-derived input does not qualify a Node input provider:
the corrected classification reports 18 browser effects and 13 Node effects,
and still says startup closure is NOT_ESTABLISHED.

Run and verify:

```sh
python3 tests/wasm/stage1/startup-runtime-review/run.py --evidence ../ccl-evidence --output /tmp/runtime-review-new
python3 tests/wasm/stage1/startup-runtime-review/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-runtime-review-r1 --output /tmp/runtime-review-replay
```

The run compiles nine functions through the unchanged compiler, reexecutes the
native oracle, runs 1,058 comparisons with 818 collections, 40 inherited owner
checks, and rejects 19 controls. Native compiler qualification is reused by
hash. The derived clock handling does not alter successful GCTIME values.
The parent raw statistics API still throws on unavailable timing; the generated
Lisp entry now handles that state before calling it.

Development: the first run failed before execution because redirecting the
parent driver directory lost its startup-joined import path; the runner now
adds that path explicitly. The next full run passed. Their logs are retained.
