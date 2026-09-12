# Project acceptance

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

Following the user's supplied fourth audit committed as `a1761aa5`, the project accepts the eighteen reviewed DYNAMIC-CALL-r1 records: S0-LL04-a/b and S0-LL13-a, plus C/C4/B variants of S0-LL05-a/b/c/d and S0-LL21-b. The separate `DYNAMIC-CALL-PROJECT-ACCEPTANCE` envelope in the [index](../evidence/index.json) retains all seven earlier acceptances exactly and adds the eighteen explicit dispositions. It contained 25 accepted records; the gate then reported 24 missing and zero unreviewed records. This is not another execution.

Acceptance is limited to the audited hand-built fixture on Node/V8 and macOS: 32 arguments, six values, bounded frames/roots/stack/replies, cons-only heap and the exact retained code. Claude's fresh 159/81 reproduction and 864 byte-identical binaries are recorded in the [fourth audit](claude-review.md). All original timestamps, test revisions, contract bindings, binaries, failure records and earlier acceptance provenance remain unchanged.

The role-rejection stand-in, capacity-based circular APPLY result and absence of a direct single-scanner inspection assertion remain disclosed nonblocking limitations. No implementation or case name is changed by this decision. Their follow-ups belong to the [measurement implementation handoff](abi-measurements.md) and production loader work. D3 timing/selection, startup, browsers, full objects, generated code, census and S0-LL21-a are excluded. H(G) remains optional.

## Fifth-audit acceptance — S0-LL21-a, 12 September 2026

The user's explicit decision, “I accept S0-LL21-a,” accepts only S0-LL21-a / full from ABI-MEASUREMENTS-r2, after Claude's fifth audit committed as `5ff0dc54`. The publication contains code identity, digest and generation; all Workers already hold the module bytes. The host actor acquires and validates the publication before installing/calling matching entries. This covers eight hand-built definitions, two existing Workers plus a late Worker, cons-only 4 KiB semispaces, and the retained Node/V8 execution on macOS. It does not establish byte delivery between Workers or Wasm-side acquisition/rejection.

The separate LL21-PROJECT-ACCEPTANCE record in the [index](../evidence/index.json) retains the original execution timestamps, test revision, contract binding, artifacts and exact fifth audit. Only the authorized review disposition and acceptance provenance are added. The combined envelope preserves the earlier 25 accepted result objects exactly. It now contains 26 accepted records; Stage 0 is BLOCKED for 23 missing records and zero unreviewed records. No fixture is changed or re-executed by this decision.

Exploratory timings remain NO_SELECTION and supply no candidate-ranking evidence. LL21-a acceptance does not approve the benchmark policy or establish D3 performance, representative weights, production scale/startup, browsers, optimized tiers, generated code or the census. The subsequent [B engineering choice](abi-choice.md) follows the user direction to stop spending effort on the comparison and choose for simplicity. Comparative measurement work is deferred; the qualified census and shared-compiler pass 2 still need an authorized author.

## Sixth-audit acceptance — S0-LL08-b, 12 September 2026

The user's decision, given directly to Claude ("I confirm the claude.md line and accept S0-LL08-b at its stated scope"), accepts only S0-LL08-b / native from NATIVE-CENSUS-r5, after Claude's sixth audit committed as `899baedc`. The same message confirms the "clean implementation start" line Codex added to `CLAUDE.md`, resolving the audit's first observation. Claude produced the envelope with the existing `accept-evidence.py` and composed the aggregate; the producer refused the output name `results.json` because the r5 pack retains an artifact of that name, so the accepted envelope is `accepted-results.json`.

Scope: evaluated native operator slots, flags and dispatch readings unchanged under a reversible three-file observation patch in a disposable U1 copy; two passing native suites; 161 of 164 FASLs identical under observation and 164 of 164 after removal; the event logs retained as census inputs. Excluded: S0-LL15-b/c closure, the external cold-start trace, S0-LL08-a and S0-LL08-c, kernel or image byte identity, and any functional compiler change.

The separate `LL08B-PROJECT-ACCEPTANCE` record in the [index](../evidence/index.json) retains every original r5 field, timestamp, test revision, contract binding and artifact, adding only the review disposition and provenance. The 27-record aggregate copies the 26 earlier accepted result objects unchanged; 104,279 artifact references were verified against retained bytes. Stage 0 is BLOCKED for 22 missing records and zero unreviewed. No fixture is changed or re-executed by this decision.