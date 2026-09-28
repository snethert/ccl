# Calling convention subtraction

Implemented against `485559e3`. The user explicitly requested one integrated
implementation and final qualification, superseding the advisory's separate
commits and repeated timing cycles. No direct calls, alternate entries, call-site
caches, result-budget changes, image saving or upstream kernel edits are included.
**Accepted after user-supplied [Claude audit 193](../stage0/claude-review.md)**
(`a2b70622`), at the user's direction on 28 September 2026. The review finds no
defect in `243761e4`; Phase 2 remains rejected.

## Admission equivalences

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

## Retained scope and rejected Phase 2

**Phase 1 is retained. Phase 2 is removed following the user's direction.**
Phase 1 reduced the default call increment from 50.614 to 28.777 ns. Since
that exceeded 15 ns, Phase 2 was implemented and measured after completing
the reader inventory. It saved only another 1.771 ns, produced no measurable
READY gain, and regressed inline numeric loops. That tradeoff did not justify
the additional contract. The [rejected experiment](call-convention-phase2-rejected.md)
retains its full inventory, measurements, source snapshot and failure evidence.

The active backend retains TCR-derived entry state, full caller publication,
normal count publication, exception restoration and ABI version 1. Runtime
adapters, publisher and corpus harness are unchanged. No context-only/static
publication contract from Phase 2 remains.

## Verification and reuse

Persistent pack: `../ccl-evidence/2026-09-28-call-convention-r1`.
The Phase 1 corpus executed **26,204 fresh comparisons**, zero failures, zero
sampled and zero inherited comparisons (203.468 seconds target execution).
Its first compilation completed before RAM exhaustion; the retained recovery
reran the incomplete native oracle from that fresh compiler checkpoint and
executed the complete corpus. The original failure and recovery are preserved.
No rejected Phase 2 corpus run is credited to the retained change.

The subsequent public-boundary metadata correction leaves every benchmark
body unchanged; its rebuilt core and three READY runs are retained exactly.
After rollback, all **29 complete benchmark code records**, including public
wrappers, match that qualified Phase 1 build. The only additional source
changes are two guards restricting pool caching to callable-metadata mode and
the corrected SELF proof comment. `wasm32-compile-file` binds both flags true;
product emission is unchanged, while the prototype API keeps its original
literal checks. The source delta and byte equality are recorded in
`kept-observations/kept-equivalence.json`. Timing and corpus runs were not
repeated simply to record the rollback.

The restored Phase 1 was rebuilt and rerun with **69 native-matched rows** and
**nine moving collections**, including cleanup and 64 retained dynamic values.
Its 45 boundary assertions pass, including checked public refusals before
writes, 0/1/4/5/64 result capacities, unchanged overflow depth 11, the exact
unconditional-helper control and 100,000 tail calls in 2 KiB. Ordinary scalar
64-value results still exceed the original budget; explicit capacity 64
succeeds, and capacity four preserves the kind-3 refusal.

Both moving-root mutants are killed by their named rows, and all fixture
public entries may trap while ordinary compiled calls still complete.
Checker mutants reject wrong answers, missing rows and missing collections.
Zero-slot, retired-version, stack reentrancy-bit and public-metadata deletion
mutants fail their boundary assertions. Four metadata producer corruptions
are refused before serialization. The unchanged publisher's 81 synchronous
and 11 asynchronous controls remain qualified. The separate 21,843-test
native R6 suite and 782 reader comparisons are reused by unchanged source
identity; no shared compiler or upstream kernel source changed.

## Measurements

All sixteen unchanged workloads ran in three fresh processes per mode and
passed all 36 benchmark moving collections. Medians below are ns per iteration;
the [machine record](call-convention-results.json) retains process ranges.

| Workload | Prior default | Native | Retained default | Liftoff | TurboFan |
|---|---:|---:|---:|---:|---:|
| EB-CALL | 53.607 | 2.485 | 32.844 | 104.980 | 34.446 |
| EB-CAR | 17.741 | 2.734 | 11.942 | 24.110 | 16.481 |
| EB-CAR-TYPED | 8.688 | 2.377 | 7.068 | 13.728 | 6.802 |
| EB-DOUBLE-GENERIC | 1657.654 | 15.851 | 1672.058 | 1847.168 | 1665.863 |
| EB-DOUBLE-TYPED | 2.762 | 2.546 | 3.034 | 5.880 | 3.730 |
| EB-EQ | 22.248 | 1.351 | 12.800 | 35.190 | 19.625 |
| EB-FIXNUM-GENERIC | 5.318 | 2.122 | 5.051 | 6.485 | 5.002 |
| EB-KEYWORD-LOOP | 82.542 | 12.182 | 47.158 | 127.686 | 49.908 |
| EB-LIVE-REFERENCE | 53.499 | 2.431 | 32.218 | 106.628 | 34.355 |
| EB-LOOP | 2.993 | 2.236 | 4.067 | 7.308 | 3.476 |
| EB-OPTIONAL-LOOP | 95.854 | 5.973 | 55.846 | 138.174 | 58.300 |
| EB-REFERENCE-CALL | 51.538 | 2.140 | 31.915 | 96.758 | 33.345 |
| EB-REST-LOOP | 319.645 | 41.917 | 111.387 | 281.147 | 127.380 |
| EB-SINGLE-TYPED | 2.755 | 2.745 | 3.017 | 5.738 | 3.021 |
| EB-SVREF | 21.810 | 3.011 | 16.500 | 35.296 | 21.347 |
| EB-SVREF-TYPED | 15.540 | 2.739 | 11.274 | 20.982 | 10.568 |

`eb-call − eb-loop` is the difference of the workload medians:

| Mode | Accepted baseline | Retained Phase 1 |
|---|---:|---:|
| native | 0.229 ns | 0.249 ns |
| default | 50.614 ns | 28.777 ns |
| liftoff | 162.039 ns | 97.672 ns |
| turbofan | 60.816 ns | 30.970 ns |

The default call increment falls **43.1%**. The inline loop rises from 2.993
to 4.067 ns; typed double/single rise from 2.762/2.755 to 3.034/3.017 ns.
Those regressions are consistent across processes; their cause is not isolated.
Call, reference, optional, rest and keyword rows improve substantially.

The corrected-public-wrapper READY runs take **19.623, 19.696 and 20.372 s**,
median **19.696 s**, with median RSS **1,629,036,544 bytes**. All load 81
runtime files using seven modules and eleven instances. The runtime archive
is **63,561,129 bytes**, **5,411,370 bytes smaller** than the 68,972,499-byte
ceiling. READY and RSS are below the accepted reference's 26.510 s and
2,211,127,296 bytes. That reference used older cores; rebuilding also includes
previously accepted numeric/accessor optimizations, so the entire startup
improvement cannot be attributed solely to this change.

## Generated-body inspection

These are complete-body static WAT counts, including cold branches. They are
not executed or machine-code instruction counts. The inspector is unchanged.

| Body / revision | Loops | Indirect calls | i32 loads | i32 stores | Root-head stores | NIL stores | `if` | Metadata helper calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EB-ADD baseline | 1 | 0 | 37 | 27 | 4 | 5 | 27 | 4 |
| EB-ADD retained | 1 | 0 | 28 | 24 | 3 | 5 | 22 | 0 |
| EB-CALL baseline | 4 | 2 | 150 | 166 | 26 | 26 | 82 | 4 |
| EB-CALL retained | 2 | 2 | 161 | 164 | 25 | 29 | 84 | 0 |

The inline guard exposes its loads and branch in the caller; unrolling
exposes individual stores. Not every static opcode count decreases. The
ordinary call path executes less work without adding another entry or path.
The two/thirteen possible stack-guard helper calls in EB-ADD/EB-CALL remain
as slow paths. Their successful reservation path bypasses the helper.

Product Lisp: **91 added / 42 removed**. Frame sizes and result budgets are
unchanged. Census **44,724,264** is inherited, not freshly measured. Originals
575/535 and ledger 21/12 are unchanged; no criterion credit is claimed.
The retained Phase 1 is reviewed and accepted. Audit 193 rebuilt the cores
from the committed backend and reproduced their bytes apart from identity
records, reran 26,204 fresh corpus comparisons, 69 rows / nine moving
collections and 45 boundary assertions, and confirmed the publication refusals
and controls. Its default call increment is 28.709 ns, READY median 19.703 s,
and archive 63,561,129 bytes. O-154 through O-158 are informational; no
producer round is required. Acceptance reuses these completed checks without
rerunning unchanged tests. The producer measurements and persistent pack
remain historical records.
