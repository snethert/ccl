# Rejected Phase 2 calling convention

**Rejected by user direction, 28 September 2026.** Phase 2 saved 1.771 ns
beyond Phase 1, did not improve READY, and regressed inline loops. Its protocol,
adapters and ABI version 2 are removed from the active implementation. All
measurements below describe the rejected experiment and are retained as evidence.

Experiment implemented against `485559e3`. The user explicitly requested one integrated
implementation and final qualification, superseding the advisory's separate
commits and repeated timing cycles. No direct calls, alternate entries, call-site
caches, result-budget changes, image saving or upstream kernel edits are included.
Independent review has not been supplied; this record does not claim acceptance.

## Phase 1 admission equivalences

| Removed work | Producer / remaining predicate | Directed evidence |
|---|---|---|
| Normal callee TCR restoration | Each caller copies its result and restores its own saved state. The public wrapper retains both restoration paths; exceptional body restoration remains. `rv_ensure` operates on its descriptor. | Fresh corpus, static/dynamic result rows, unwinding and moving references. Restoring the omitted stores is an equivalent control, not a killed semantic mutant. |
| Repeated internal/tail table checks | Resolver checks dynamic node, function, id, version and nonzero slot. Registry and paired tables are owned by synchronous publication; no Lisp/collection occurs during their transaction. A lazy slot holds a non-null checked thunk. | Zero-slot and retired-version refusals; removing each remaining check is killed. Public entries replaced by traps for the focused fixture. |
| Duplicate context `prev` store | Root writer receives the saved predecessor directly. APPLY passes its evaluation frame and still retires that frame only after copying all arguments. | APPLY, closures and moving-argument rows; corpus. |
| Constant argument-root fill loop and simple-operand prefill | Literal counts are unrolled. `b-simple-node-p` excludes allocation, polling, boxing and checked type operations. SELF is stored first; a local-self helper can signal before that store, while no new node slot is live. All argument reads follow it and cannot collect. Final slots are filled in Lisp evaluation order before publication. | Moving cons argument; remove its early root publication as an unsafe-staging mutant. |
| Repeated product metadata validation | `metadata-check-pool` checks shape, format versions and required/optional counts in `pool-plan`, before serialization. Authenticated image/FASL bytes and code-record identity bind them to publication. `$fasl-wasm32-function` assigns the first two pool words to the function fields; `b-make-closure` copies the same compiled child pool through checked `metadata-child-load`. Product metadata structure is compiler-owned after publication. | Producer corruption refusals, authenticated bundle/image admission controls and moving pool/closure witnesses. Prototype entries retain their checks. The public host wrapper keeps full SELF/pool/metadata validation before writing any frame. |
| Per-literal function and pool validation | Cache the tagged pool in existing context root slot `+44`, after entry. Every subsequent load reads the relocated root. Frame size and root count are unchanged. | Pool identity across a forced collection; caching an untraced local is a killed mutant. |
| Internal frame validity checks | Generated callers reserve extents with wide arithmetic; the public wrapper validates its supplied frame before writing. Internal entry is an owner capability, not a public untrusted ABI. | Public malformed-frame refusals preserve all memory; compiled-public-entry trap control. |
| Repeated stack-layout checks in reservations | Public entry checks alignment, base/limit ordering, reserve span and memory extent before publication. Stack bounds/reserve are owner-controlled during execution. Inline reservation compares wide end with `limit-reserve`; the original helper owns overflow, hard limit and reentrancy. | Exact threshold and checked refusals, reserve-bit mutant, corpus stack/cleanup witnesses. |
| Registry alignment/header/span, row signature/role and table extent/null checks | `admitCodeArchive`, `admitTargetBundle`, `admitCrossImage`, `BindingInstaller` and `LazyLoader` admit registry/table extents and entries. Transactions exclude execution, install both tables and roll back on failure. | Publication controls and resolver dynamic refusals. Node span, function header, id/version representation, id capacity, version equality and zero slot remain checked. |

The advisory's bare untagged `$pool` local is unsafe: target-loaded pools move.
Using an existing traced slot avoids adding a root or changing a budget. The
optional second callee-fill implementation for capacity four is omitted: it
duplicates a fill path and adds a branch. Runtime frame capacity still follows
the unchanged caller budget.

Supported function mutation was inspected in `bootstrap-function-immediate`,
`bootstrap-set-function-bits` and `bootstrap-make-funcallable`: they modify the
separate funcallable immediates vector or copy an admitted function, preserving
the compiled pool and arity/debug identities. `%copy-function` has no Wasm
implementation in this parent. Raw mutation of compiler-owned pool metadata
after publication is outside this equivalence; a post-publication arbitrary
memory corruption cannot logically be refused by an earlier check. Publication
corruption controls must therefore act before authentication/publication.

## Reader inventory before any Phase 2 change

The fourteen original `tcr.vsp` readers are classified by function, so line
movement does not change the inventory. A = compiled context/local state;
B = service or control boundary requiring a consistent published state;
C = collector.

| Original site | Class | Treatment required for a thinner static protocol |
|---|---|---|
| `emit-expression` lexical argument (76) | A | Legacy scalar emitter; product `b-read-variable` reads incoming roots. |
| `b-call` tail staging (869) | A | Saved TCR state is dead after `return_call_indirect`; tail transfer derives delivery from its context. |
| `b-prepare-context` (899) | A | Raw saved caller words; internal callee derives its actual arguments/output from context. |
| `b-internal-call` (929) | A | Save/publish/restore MV/VSP state only for dynamic delivery. Root publication remains universal. |
| `b-control-frame` (1030) | B | Retain catcher snapshot/restoration. Zero MV count permits consistent older bounds. |
| `b-exit-frame` (1100) | B | Retain nonlocal-exit snapshot/restoration. |
| `b-multiple-call` (1228) | A/B | Dynamic producer descriptors and service boundaries require independent treatment. |
| `b-one-module` (1518) | A | Incoming/root are context+48/+32; output=context+4, owner=context. Incoming count is the protocol constant zero, rather than the caller's older count saved in context+16. |
| `b-apply` tail staging (1622) | A | Same continuation ownership as tail call. |
| `b-internal-apply` (1694) | A | Same dynamic-only TCR publication as ordinary internal call. |
| `b-entry-wrapper` (2148) | B | Keep the public host contract and checks. |
| Both `b-implicit-runtime` variants (2585,2637) | B | Retain signal-handler snapshot, argument publication and restoration. |
| Final bootstrap implicit-error runtime (6582) | B | Same signal boundary; cannot simply delete its stores. |

The `mv_base`, `mv_owner_top`, and `mv_count` reads accompany these snapshots,
entry/public wrapper loads and observer emitters. Runtime readers outside the
backend require these additional obligations:

| Runtime reader | Class | Required treatment |
|---|---|---|
| `collector.c` active results at +116/+120/+124 | C | A zero count still requires valid bounds; dynamic unrooted results require their actual count and addresses. |
| `CollectorOwner.#validateLive` result ownership | C | Stale zero-count bounds must remain inside the owned stack/temp extent. |
| `CollectorOwner.validObject` VSP stack-function frontier | B | Current frontier is needed at this service boundary, not merely a consistent old VSP. |
| `fileClient.run` VSP/argument equality | B | Its adapter must publish the actual rooted argument pointer around the host service. |
| `host-call-adapter.wat`, `target-code-adapter.wat` | B | Derive arguments/static output from context; publish current VSP around the service, restoring it on normal and exceptional exits. Keep dynamic result publication. |
| `symbol-adapter.wat`, `hash-adapter.wat` | B | Derive arguments/static output from context; these C leaves do not read VSP. Keep dynamic result publication; collection sees consistent older zero-count bounds. |

These runtime readers mean the advisory's backend-only Phase 2 deletion is not
sufficient. Any implementation must account for the service adapters too.

## Phase 1 gate and Phase 2 decisions

Phase 1 completed before Phase 2 began. The fresh corpus passed all 26,204
cases. The unchanged sixteen workloads ran in three isolated processes for
each of native, default, Liftoff and TurboFan. Median `eb-call − eb-loop`
was 0.249 ns native, 28.777 ns default, 97.672 ns Liftoff and 30.970 ns
TurboFan. The accepted prior default increment was 50.6 ns. The increment
remained above 15 ns, authorizing the conditional Phase 2 work.

The public metadata-boundary correction preserved all 29 benchmark module body
AST hashes. Its rebuilt runtime archive was 63,561,129 bytes, below the
68,972,499-byte ceiling. Its three READY times were 19.623, 19.696 and
20.372 seconds (median 19.696), with a median RSS of 1,629,036,544 bytes.
The earlier full timing series and its original artifacts are retained too;
they are not presented as measurements of a later binary.

Phase 2 removes the ordinary static caller's four TCR snapshots,
publications and restores, derives callee state from context, and suppresses
the normal static count store. Root publication remains mandatory. The
unused internal context snapshots and dead code following tail transfers
are removed; reservation sizes remain identical. Rebuilt artifacts declare
ABI version 2 so the loader refuses old archives before publication. The [experimental contract](#rejected-contract)
states the copy interval and service boundaries.

The exception scaffold is retained. Small scratch does not prove that
delivery is static: the same function can deliver into a dynamic descriptor.
Moreover, exceptional restoration and the enclosing control snapshots keep
the zero-count bounds consistent before cleanup resumes Lisp. `eb-add` does
not satisfy the existing small-scratch predicate; extending that proof or
changing budgets is outside this subtraction.

The advisory's dynamic-count GC mutant is not a sensitive oracle for the
current descriptor protocol: values are already rooted in descriptors, and
capacity growth occurs before the final count store. This change instead
kills deletion of that store by checking the actual dynamic TCR counts,
including 5 and 64, and independently exercises 64 retained references
across moving collection. No claim is made that the suggested GC mutant
was killed. The static copy-window mutant inserts a real collecting owner
call after return and before the caller's copy.

## Verification record

Persistent pack: `../ccl-evidence/2026-09-28-call-convention-r1`.
Original storage-exhaustion and static-budget probe failures are retained under
`development/`. The initial corpus compile completed before RAM exhaustion;
recovery reruns its incomplete native oracle from the fresh compiler image,
checks retained proposal sources against the checkout, then assembles and
executes the full corpus. No SSD compilation fallback is used.

The first Phase 2 corpus exposed two historical test leaves still using the
old publication protocol: the hash adapter and its EQL variant. The existing
`prepare_execution_runtime` extension now rebuilds the hash adapter and adapts
only the four delivery clauses of the pinned EQL leaf, preserving its EQL
operation. All adapted source/binary hashes enter the execution environment.
The original failure and the 48-comparison passing diagnosis are retained.

Review also narrowed pool caching to callable-metadata product mode, keeping
the older bootstrap API's original literal validation. All 29 product benchmark
code records, including public wrappers, remained identical after that guard.
The final corpus is rebuilt after this correction; no failed or earlier corpus
execution is credited as a final comparison.

The final fresh full corpus passes **26,204/26,204**, with zero sampled and
zero inherited comparisons (196.404 seconds target execution). The native
oracle is fresh. The separate native R6 suite's **21,843/21,843** result and
reader evidence are reused by identity: 65 non-Wasm/shared source hashes match
the accepted declared-accessors qualification, and no shared compiler or
upstream kernel source changes are present.

The final ABI version 2 focused startup passes **69 native-matched rows** and
**nine moving collections**. Boundary controls pass 56 assertions, including
unchanged depth 11 overflow, the unconditional-guard equivalence control,
100,000 tail steps in 2 KiB, static TCR preservation and dynamic counts through
64. Sixteen service-adapter cases cover both delivery modes and both exits.
Four producer metadata corruptions are refused before a bundle is published.

The three semantic mutants reach READY and fail their named observations:
argument rooting changes `:ARGUMENT T` to `NIL`; an untraced pool changes
`:POOL (T 303)` to `(NIL 303)`; two collections in the static copy interval
change `:RETURN T` to `NIL`. Zero-slot, version, stack-signal, public metadata
and dynamic-count deletion mutants fail their boundary assertions. Checker
mutants reject wrong/missing rows and missing collections. Making every
fixture public entry trap still permits all ordinary compiled calls to finish.

Those semantic mutants executed on code records identical to the final
product records; the final ABI label is separately exercised by the complete
focused startup and an old-archive refusal before publication. The unchanged
publisher also passed 81 synchronous controls and 11 asynchronous checks.
The invalid initial copy-window WAT mutant is retained as a tooling failure,
not credited as a killed semantic mutant.

The only backend edit after the final corpus/core build was the recorded
SELF-staging proof comment. Exact before/after text and hashes are retained.
The timing harness refused the older benchmark's source hash before collecting
any samples; rebuilding the benchmark preserved all 29 code records exactly.
No executable source difference is hidden by that qualification reuse.

## Generated-body inspection

These are static WAT counts across the complete body, including cold paths,
dynamic delivery and exception restoration. They are not executed instruction
counts or machine-code counts. The inspector and benchmark source are unchanged.

| Body / revision | Loops | Indirect calls | i32 loads | i32 stores | Root-head stores | NIL stores | `if` | Metadata helper calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EB-ADD accepted baseline | 1 | 0 | 37 | 27 | 4 | 5 | 27 | 4 |
| EB-ADD Phase 1 | 1 | 0 | 28 | 24 | 3 | 5 | 22 | 0 |
| EB-ADD final | 1 | 0 | 24 | 24 | 3 | 5 | 23 | 0 |
| EB-CALL accepted baseline | 4 | 2 | 150 | 166 | 26 | 26 | 82 | 4 |
| EB-CALL Phase 1 | 2 | 2 | 161 | 164 | 25 | 29 | 84 | 0 |
| EB-CALL final | 2 | 2 | 153 | 156 | 25 | 29 | 91 | 0 |

Inlining the guard exposes its loads and branch in the caller; unrolling a
constant fill exposes individual stores. Phase 2 adds branches around the
retained dynamic protocol. Those source counts therefore do not all decrease,
even though the ordinary static path executes less work. The remaining
EB-ADD fill loop and exception scaffold follow the unchanged scratch policy.
Both versions retain two and thirteen possible stack-guard calls in EB-ADD
and EB-CALL respectively; the inline condition now bypasses the helper on
successful reservations. Full inspection records include every workload.

## Final measurements

The unchanged sixteen workloads passed in three fresh processes per mode,
including all 36 benchmark moving-collection witnesses. Values below are the
median of three process medians, in ns per iteration. Raw process ranges and
samples are retained in the [machine record](call-convention-phase2-rejected.json)
and evidence pack. Native is the current rerun; the baseline column is the
accepted declared-accessors default V8 result.

| Workload | Baseline default | Phase 1 default | Native | Final default | Liftoff | TurboFan |
|---|---:|---:|---:|---:|---:|---:|
| EB-CALL | 53.607 | 32.844 | 2.502 | 31.522 | 93.732 | 32.380 |
| EB-CAR | 17.741 | 11.942 | 2.722 | 13.245 | 23.645 | 17.545 |
| EB-CAR-TYPED | 8.688 | 7.068 | 2.383 | 7.840 | 13.594 | 7.683 |
| EB-DOUBLE-GENERIC | 1657.654 | 1672.058 | 16.466 | 1663.025 | 1866.394 | 1645.020 |
| EB-DOUBLE-TYPED | 2.762 | 3.034 | 2.551 | 4.520 | 6.029 | 3.861 |
| EB-EQ | 22.248 | 12.800 | 1.766 | 13.151 | 34.727 | 20.231 |
| EB-FIXNUM-GENERIC | 5.318 | 5.051 | 2.096 | 5.276 | 7.037 | 5.308 |
| EB-KEYWORD-LOOP | 82.542 | 47.158 | 11.480 | 44.033 | 115.643 | 45.662 |
| EB-LIVE-REFERENCE | 53.499 | 32.218 | 2.414 | 30.379 | 93.581 | 32.660 |
| EB-LOOP | 2.993 | 4.067 | 2.218 | 4.517 | 7.016 | 4.151 |
| EB-OPTIONAL-LOOP | 95.854 | 55.846 | 5.178 | 52.899 | 129.166 | 55.914 |
| EB-REFERENCE-CALL | 51.538 | 31.915 | 2.131 | 30.478 | 93.553 | 32.750 |
| EB-REST-LOOP | 319.645 | 111.387 | 41.906 | 104.790 | 272.125 | 115.286 |
| EB-SINGLE-TYPED | 2.755 | 3.017 | 2.762 | 4.484 | 6.009 | 3.829 |
| EB-SVREF | 21.810 | 16.500 | 3.007 | 17.549 | 34.860 | 22.584 |
| EB-SVREF-TYPED | 15.540 | 11.274 | 2.989 | 12.176 | 20.713 | 12.482 |

`eb-call − eb-loop` is the difference of the workload medians above:

| Mode | Accepted baseline | Phase 1 | Final |
|---|---:|---:|---:|
| native | 0.229 ns | 0.249 ns | 0.284 ns |
| default | 50.614 ns | 28.777 ns | 27.005 ns |
| liftoff | 162.039 ns | 97.672 ns | 86.716 ns |
| turbofan | 60.816 ns | 30.970 ns | 28.228 ns |

The default increment falls **50.614 → 27.005 ns (46.6%)**. Phase 2 provides
another 1.771 ns (6.2%) beyond Phase 1; it does not reach the advisory's
approximately 10 ns aspiration. The tiny inline loop rises from 2.993 to
4.517 ns, and typed double/single rise from 2.762/2.755 to 4.520/4.484 ns.
These regressions appear in all three processes; their cause has not been
isolated. Call, reference, optional, rest and keyword rows all improve.
This is not a claim that every workload becomes faster.

Ordinary READY takes **19.709, 19.929 and 19.789 seconds**, median **19.789**.
Median RSS at READY is **1,651,798,016 bytes**, with a 1,661,972,480-byte
median peak. All runs load 81 files, with seven product modules and eleven
instances. This overlaps Phase 1's 19.623–20.372-second range; no material
further READY improvement is claimed for Phase 2.

The runtime archive is **61,904,166 bytes**, **7,068,333 bytes smaller** than
the 68,972,499-byte ceiling. It also shrinks from the corrected Phase 1
archive's 63,561,129 bytes. READY and RSS are below the accepted reference's
26.510 seconds and 2,211,127,296 bytes. That reference used older core
archives; these rebuilt cores also incorporate the previously accepted
numeric/accessor improvements. The whole startup gain cannot be attributed
solely to this calling-convention change.

Product Lisp changes: **140 added / 104 removed**. Subtraction refers to
work executed by the ordinary call protocol, not a requirement that emitter
source lines or every static opcode count decrease. No second call path or
specialized entry is introduced. Census **44,724,264** is inherited from the
accepted census and was not rerun here. Originals 575/535 and ledger 21/12
are unchanged; no criterion credit is claimed. This integrated deliverable
passed producer checks but is rejected; no acceptance is sought for Phase 2.


## Rejected contract



This contract was tested and then rejected. It does not apply to the active tree.
It preserves public entry, frame sizes, result budgets and paired indirect
tables. Newly built artifacts declare ABI version 2: mixing an archive using
the older internal protocol is refused by the loader's version check.
Internal entry derives incoming arguments at `context+48`, its root
record at `context+32`, its output from `context+4`, and its output bound from
`context` itself. The incoming result count is zero. Header words 0, 8, 12 and
16 are reserved in internal contexts; the public wrapper still writes its
original snapshots. Delivery mode, ephemeral extent and dynamic descriptor
remain at offsets 20, 24 and 28. The second traced context slot at +44 holds
the pool, which the collector relocates along with SELF and arguments.

Ordinary static calls publish roots but do not save, publish or restore VSP
or the three MV fields on normal delivery. There is no safepoint between the
callee copying results into its untraced output reservation and the caller
copying them into rooted scratch. Only local operations, capacity refusal
through a checked Wasm exception, and the copy occur in that interval. Adding
a poll, allocation, Lisp call or collecting helper there changes the contract
and requires result rooting before it. Static return does not publish a count.

Dynamic delivery retains its caller publication and restoration and its
callee count store. Dynamic descriptors separately root their values; the
existing delivery/capacity helpers and their safepoints remain unchanged.
The count store does not authorize inserting an arbitrary safepoint anywhere
in the return sequence.

Exception restoration remains in the callee. It publishes consistent entry
bounds and a zero count while propagating the exception; CATCH, cleanup and
public boundaries restore their saved state before resuming Lisp. The
exception scaffold is retained because dynamic delivery and cleanup still
have obligations even when scratch allocation is statically small.

Host-call and target-code adapters publish the actual argument frontier
around their synchronous service and restore it on both exits. Symbol/hash
leaves derive output from context and need no VSP publication. All adapters
retain dynamic result publication. These service boundaries are distinct
from the static result-copy interval.
