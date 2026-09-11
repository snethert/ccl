# Project acceptance — 11 September 2026

The user authorized proceeding after Claude's sign-off committed as `52639e4e`. The project accepts exactly the seven identified execution records below, within their recorded scopes. This is a review-disposition operation; it does not claim another execution.

| Accepted record | Scope |
| --- | --- |
| G0-U1-a, macos-x86-64 | Unchanged U1 native execution and same-host repeatability: two clean builds, 21,843 passing eligible tests per build and 164 identical FASLs. Second-Mac reproduction remains open. |
| S0-LL13-c / S0-LL19-b, full | Reviewed hand-built C-boundary and exceptional-restoration slices at the retained fixture bounds. |
| S0-LL20-a/b/c, full | Reviewed hand-built, cons-only moving-GC/admission/lifecycle/I/O slices: 22 cases, 14 controls and 1,000 seeded schedules. |
| S0-LL23-b, full | Reviewed logical debugger-frame slice: eleven cases and eleven controls. Shared-cell relocation is a surrogate; policy-1 unavailability does not establish optimized storage cost. |

The [evidence index](../evidence/index.json) identifies PROJECT-ACCEPTANCE-2026-09-11, its exact accepted envelope and explicit decision. That envelope retains every original timestamp, test revision, contract digest and artifact byte. It adds the exact [Claude review](claude-review.md), the user's authorization and per-record scope. The original preacceptance envelopes remain unchanged and retrievable. The producer is [accept-evidence.py](../tools/accept-evidence.py); fourteen controls check scope, identity, failure rejection and preservation without granting acceptance to test fixtures.

This decision removes seven unreviewed reasons from the previous 49-reason gate. The resulting 42 missing obligations remain open. Subsequent executions can replace a missing reason with an unreviewed reason, but cannot silently gain acceptance from this decision. In particular, the new C/C4/B dynamic-call fixture, its C extension and newly linked kernel require their own independent review and project acceptance.

This accepts neither Stage 0 as a whole nor D3 selection, production scale, startup, browser support, generated code, complete object schemas or the census. The initial probes remain diagnostic only. H(G) remains optional future work.
