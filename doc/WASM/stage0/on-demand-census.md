# On-demand census — 15 September 2026

The census now has a usable query and native call-site witness tool. Its
[README](../../../tests/wasm/native-census/query/README.md) supplies complete
commands. `query/run.py` answers retained-build questions, lists source-derived
call sites, and probes a selected site under a supplied native scenario in a
disposable pristine U1 copy. It requires no historical temporary directory.

The user first requested the tools and a concrete policy revision, then said:
“I will approve the change, so treat it as approved”. This authorizes the
[v0.2 census contract](../contracts/census.md), not acceptance of an unreviewed
test result. LL15-b/c now qualify the instrument, explicit worklist and independent
omission/semantic controls. Exhaustively bounding all native computed calls no
longer gates Stage 0. The complete-closure checker stays unchanged and blocked
on unresolved required edges. Stage 1 still owes a working generated bootstrap,
its dependencies, initializer order and completion.

The rationale is practical: observations and identity joins are mature, while
calls through parameters, mutable slots and registries are dynamic by design.
Use a retained base and focused native scenarios to answer implementation
questions. Preserve unknowns and proven bounds separately; a witnessed callee
does not become the set of every possible callee. This is a dated project
decision, not an experimentally established completeness result.

## Delivered cut point

- The correlated build r3, its original baseline, reversible observation,
  before/after tests, recovery comparisons and two failures are retained in
  `CORRELATED-QUERY-BASE-R1` in the evidence repository. The large native event
  streams no longer depend on temporary storage.
- The [fresh finite-expression replay](finite-callees.md) now establishes 124
  proofs and 1,438 original rich-build expressions still open from one committed
  resolver version. The earlier claim that all 4,373 read-only body joins were
  finished is [withdrawn as a qualified delivery](registry-history.md): the
  complete old chain lacked executed-source provenance. Its raw artifacts are
  retained as history. These populations are not counts to add to the new
  correlated execution.
- The last full source compile completed all 167 units with reference/observed
  native code identical, source unchanged and no FASLs written. Its transitive
  startup graph has 16,169 nodes and 36,848 edges, reaching 4,369 native functions:
  3,556 source bodies, 541 runtime bodies and 272 missing bodies (27 sourced,
  245 unsourced). There are 2,859 initial function cells and 394 reached generic
  registries. This is the retained worklist, not a complete closure. It supersedes
  the narrower 84-unit diagnostic for current startup work; it erases no old
  evidence or obligations.
- Full traversal exposed legitimate changes to newly created generic functions
  as methods were installed. The body join now requires actual registry evidence
  and preserves their first entry-code descriptor; it never uses the final
  changed code as a source-body match. Selected startup functions remain subject
  to the stricter unchanged-code check. Four damaged witnesses are refused.

## Executed tool checks

The retained query index covers 51,341 compiler functions, 103,392 call sites,
36,381 binding events, 73,872 native bodies, 4,369 registry records and 51,600
materialization records in the correlated execution. Twenty-seven NIL-name
binding events remain individually queryable without a fabricated symbol ID.
The 33 query checks include comparisons with raw native events and refusals for
damaged members/caches, missing or reordered events, invalid query identities
and misplaced completion. Three same-name GETF-TEST compilations are retained
separately; name equality is not function identity.

Twenty native probe cases pass, including a real U1 GETF-TEST recompilation,
multiple and zero values, APPLY, argument order, late symbol redefinition,
escaping closures, nonlocal cleanup, callee errors, unreached/truncated cases,
four incorrect selections and four rejected observer mutants. The public CLI
also prepares a pristine U1 copy and runs the real source-site example.

The probe supports unique top-level DEFUN forms and ordinary front-end CALL
sites, including nested functions. It does not yet recreate arbitrary method or
top-level macro environments. A selected target is logged before dispatch;
entry and completion are not asserted. The caller supplies a scenario that
sets up/resets relevant state and checks effects. Reference/observed/restored
results are compared using EQUALP, and uncaught errors by condition type; this
does not compare every side effect or error message. Native IDs have invocation
scope. Unreached and truncated runs cannot qualify a positive witness.

The packet retains the 900-second full-compile timeout, the first final-registry
refusal, the initial missing-environment probe failure, the first unkeyed-binding
index refusal and the corrected test-oracle failure. Successful runs do not
overwrite those originals. No shared source, kernel, production gate or census
checker changed. Claude's fifty-seventh audit (`224a27d9`) reproduced the
tools and startup worklist, and found one provenance defect: the combined
graph in the original packet used an unretained intermediate base. Its
standalone startup populations were verified; that combined artifact is
superseded, not qualified by those checks.

`ON-DEMAND-STARTUP-R2` replays all three analysis stages from the retained 167-unit
capture on the reviewed finite-chain base `6d30938b…`. The
`query/replay_startup.py` command records the actual analysis invocations and
executed sources and compares the outputs to the retained worklist. It makes
no new native-execution claim. The original packet remains immutable, including
the defective combined graph; only the corrected graph should be used for
future combined analysis. Correction evidence and its review are separate
from the unchanged query/probe results.

The replay passed: all 26 body/binding analysis files are byte-identical,
and every startup-graph field except the inherited profile is identical.
The combined graph contains exactly the retained base plus the startup
worklist: 385,903 nodes and 1,126,896 edges. No old working graph is an input.

## Remaining publication work

LL15-b/c remain NOT_RUN with no acceptance envelope. Register a bounded
qualification runner joining these tools and retained inputs to the v0.2
requirements, exercise the remaining publication omissions and scope-promotion
controls, then obtain independent review and project acceptance. Do not resume
an exhaustive resolver loop to drive the worklist to zero. The eight missing
Stage 0 slots and forty earlier acceptances are unchanged by this decision.
