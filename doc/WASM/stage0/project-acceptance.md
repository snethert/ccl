# Project acceptance — 11 September 2026

The user authorized proceeding after Claude's sign-off committed as `52639e4e`. The first decision accepts exactly the seven identified execution records below, within their recorded scopes. This is a review-disposition operation; it does not claim another execution.

| Accepted record | Scope |
| --- | --- |
| G0-U1-a, macos-x86-64 | Unchanged U1 native execution and same-host repeatability: two clean builds, 21,843 passing eligible tests per build and 164 identical FASLs. Second-Mac reproduction remains open. |
| S0-LL13-c / S0-LL19-b, full | Reviewed hand-built C-boundary and exceptional-restoration slices at the retained fixture bounds. |
| S0-LL20-a/b/c, full | Reviewed hand-built, cons-only moving-GC/admission/lifecycle/I/O slices: 22 cases, 14 controls and 1,000 seeded schedules. |
| S0-LL23-b, full | Reviewed logical debugger-frame slice: eleven cases and eleven controls. Shared-cell relocation is a surrogate; policy-1 unavailability does not establish optimized storage cost. |

The [evidence index](../evidence/index.json) identifies PROJECT-ACCEPTANCE-2026-09-11, its exact accepted envelope and explicit decision. That envelope retains every original timestamp, test revision, contract digest and artifact byte. It adds the exact [Claude review](claude-review.md), the user's authorization and per-record scope. The original preacceptance envelopes remain unchanged and retrievable. The producer is [accept-evidence.py](../tools/accept-evidence.py); fourteen controls check scope, identity, failure rejection and preservation without granting acceptance to test fixtures.

That first decision removed seven unreviewed reasons from the 49-reason gate and left 42 missing obligations. Subsequent executions can replace a missing reason with an unreviewed reason, but cannot silently gain acceptance from this decision. At that point, the new C/C4/B dynamic-call fixture, its C extension and newly linked kernel required their own independent review and project acceptance; the fourth-audit decision below now records that separate step.

This accepts neither Stage 0 as a whole nor D3 selection, production scale, startup, browser support, generated code, complete object schemas or the census. The initial probes remain diagnostic only. H(G) remains optional future work.

## Fourth-audit acceptance — 18 C/C4/B records

Following the user's supplied fourth audit committed as `a1761aa5`, the project accepts the eighteen reviewed DYNAMIC-CALL-r1 records: S0-LL04-a/b and S0-LL13-a, plus C/C4/B variants of S0-LL05-a/b/c/d and S0-LL21-b. The separate `DYNAMIC-CALL-PROJECT-ACCEPTANCE` envelope in the [index](../evidence/index.json) retains all seven earlier acceptances exactly and adds the eighteen explicit dispositions. It contains 25 accepted records; the gate now reports 24 missing and zero unreviewed records. This is not another execution.

Acceptance is limited to the audited hand-built fixture on Node/V8 and macOS: 32 arguments, six values, bounded frames/roots/stack/replies, cons-only heap and the exact retained code. Claude's fresh 159/81 reproduction and 864 byte-identical binaries are recorded in the [fourth audit](claude-review.md). All original timestamps, test revisions, contract bindings, binaries, failure records and earlier acceptance provenance remain unchanged.

The role-rejection stand-in, capacity-based circular APPLY result and absence of a direct single-scanner inspection assertion remain disclosed nonblocking limitations. No implementation or case name is changed by this decision. Their follow-ups belong to the [measurement implementation handoff](abi-measurements.md) and production loader work. D3 timing/selection, startup, browsers, full objects, generated code, census and S0-LL21-a are excluded. H(G) remains optional.
