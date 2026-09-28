# Stage 1 closure — 28 September 2026

**CLOSED at retained evidence scopes, with explicit deferrals. Stage 2 is open.**
The user directed: “just close it. we dont need a review.”
[S1-CLOSE-2026-09-28](../decisions.md#28-september-2026--stage-1-closure)
authorizes this records-only closure. No product test or independent review
was run for it. Audits 188, 190 and 193 and their acceptances remain the runtime
qualification. Artifact retention already landed in `45682a83`, before closure.

The [current ledger](../evidence/current-stage1-gate-result.json) accounts for
all 33 slots: 21 unchanged historical acceptances and 12 now accepted at their
retained scopes. There are zero missing or unreviewed slots. This is a scoped
stage closure with declared deferrals, not a claim that every sentence of the
original inventory has a passing execution. The [binding record](closure.json)
contains exact paths, hashes, coverage denominators and each deferred portion.
It preserves the original aggregate and does not rewrite its contract bindings.
[Record verification](closure-verification.json) confirms the 44 retained
references, unchanged prior aggregate, exact 33-slot accounting and document
consistency. Product tests, compiler runs and review runs for closure: zero.

## Exit checklist and Stage 1 map

| Subgate / exit | Disposition | Evidence |
| --- | --- | --- |
| 1A: registration, native preservation, diagnostics | Closed; 3 prior accepted slots | LL08-a, LL22-b, LL23-a in the unchanged 21-record aggregate |
| 1B: representation, conversions, B calls, constants | Closed; 5 prior accepted slots | LL04-a, LL07-a, LL05-a/b, LL10-a |
| 1C: control, bindings, temporaries, closures, aliases, dispatch, numerics | Closed; 7 prior accepted slots | LL19-a, LL17-a, LL06-a, LL12-a, LL11-a/b, LL16-a |
| 1D: collector and moving EQ tables | Closed; 2 prior accepted slots | LL18-a/b; weak-table breadth continues in Stage 2 |
| 1E: materialization, granularity, symbols, installation | Closed; 4 prior accepted slots | LL21-a/b, LL09-a, LL13-a; consolidation accepted after audit 188 |
| 1E: selected initialization, fresh load, namespace, READY | Closed at A2 scope; 4 newly bound slots | LL15-a, LL14-a, NAMESPACE-a, LOADER-a; READY and error recovery in audits 188/190/193 |
| Compiler coverage extension | Closed at measured scope; 2 newly bound slots; broader attribution deferred | LL15-c/d; 82 compiled files, 5,028 observed logical functions; counts below |
| 1F: production refusals and identity | Closed at retained scope; 5 newly bound slots; unretained extensions deferred | LL01-a, LL02-a, LL03-a, LL22-a, LL24-a; archive controls, owner admission and identity checks |
| 1F: contracts | Closed at pinned versions; 1 newly bound slot; exhaustive new row join deferred | CONTRACTS-a; exact current contract hashes in closure.json |

## The twelve bindings

Evidence labels below resolve to the hash-bound references in `closure.json`.
Every unretained extension is explicitly deferred by S1-CLOSE-2026-09-28;
the original assertion text remains in the inventory for continuing work.

| Slot | Retained evidence and accepted scope | Deferred portion / continuing boundary |
| --- | --- | --- |
| LL15-a | `ready`, `load-order`, `callbacks`: level-0-only boot, real target loading and startup; omitted bundle and empty namespace refuse | A2 exclusions, including 13 callbacks, native scheduling, listener and in-image compiler |
| LL14-a | Two fresh instances, common heap/code identity, independent 111/222 state and later 112/223 results; audited rebuilds | Stage 5 application saving; retired host-cross-loaded prefix remains historical |
| LOADER-a | READY and class error transition; audit 190's catchable exhaustion, recovery and later LOAD | Multi-Worker scheduling and browser READY |
| NAMESPACE-a | Selected runtime bundles and post-image LOAD through the real file service; no leaked sessions | JSPI (entry decision, 16 September), source LOAD/in-image compiler and full stdio/provider qualification |
| LL01-a | Required-input/no-load refusals, archive reservation/instantiation/publication rollback, owner admission, generation refusal | Unretained production early/middle/late initializer, failed-child and timeout matrix |
| LL02-a | Missing entries/counts, substituted records, invalid words and publication controls; accepted behavioral mutants | Stage 1 result-ID omission and artifact-quarantine demonstration |
| LL03-a | Classification, template, materializer and installation-record identity controls | Literal hand-built-for-generated result-envelope substitution |
| LL22-a | Archive/body/helper/container digests, registry/table identity, reuse and fresh-build refusal; retained compaction provenance | Exhaustive current-envelope rebinding; historical accepted records retain their original snapshots |
| LL24-a | This current ledger, inventory reconciliation, separate history, explicit authorization and identified delivery | None for this records-only disposition |
| CONTRACTS-a | Current contract files by hash; layout v1, production TCR v2, generated B ABI v1 and ownership/materialization evidence | A new exhaustive every-row generated-fixture join; historical draft documents keep their original scope |
| LL15-c | Selected files and observed identity census; retained corpus has 877 definition rows using 126 distinct operators | Full READY operator/operand/flag/nested-function denominator and per-operator GC/unwind join are unknown, explicitly deferred |
| LL15-d | Source branches and installed identities; existing native-matched original floor 575 executed / 535 non-NIL | Broader original-body denominator and form-level replacement attribution; no additional original credit |

## Measured coverage

- **82/82 selected runtime files compiled**, without a compilation stop. The
  denominator is the retained boot-order profile, not the broader 167-unit
  native reference. The outer level-1 handoff explains **81 returning runtime
  loads**; each fresh instance also completes two post-image loads.
- **5,028 logical functions executed** in the traced READY instance, and
  **5,028/5,028 observed identities** are joined to installed code. This
  denominator is the observed startup census, not all compiled/callable bodies.
- READY operator coverage and exhaustive native-matched original-body coverage
  have **unknown denominators** in this binding. They are deferred, not reported
  as 100 percent. The separate retained corpus operator census establishes its
  own scope only. Anonymous/generated functions and primitive-name matches
  confer no additional unchanged-original execution credit.
- The previously accepted **575/535** original-body execution floor remains;
  historical admission **2,050/2,231** is not recounted or promoted here.

## Stage 2

The user's 26 September order, reiterated in this closure request, opens work
on the **foreign-function lower layer and weak hash tables**. The foreign
boundary follows [HOSTFM P2](../host-and-foreign-modules.md): typed entries,
separate memory, explicit copying/ownership, FOREIGN transitions, callbacks,
moving GC, trap containment and retirement, with FMT-1–FMT-9 under both
providers. Weak-table work continues the weak-key/value implementation already
reviewed in audits 185/186 and qualifies its production behavior under movement.

The per-slot deferrals above and existing O-136, O-139 and O-149 observations
remain visible. This closure changes no runtime behavior and starts no new
implementation or test run.
