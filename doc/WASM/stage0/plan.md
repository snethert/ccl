# Stage 0 execution plan

This plan decomposes the existing Stage 0 exit criteria. No subgate completion removes continuing regressions or later compiler-generated obligations. `inventory.json` carries the exact expected IDs; `obligations.json` is generated from the register. Status belongs in `../STATUS.md` and identified execution records, not inferred from file existence.

| Subgate | Prerequisites | Concrete deliverable and exit observation |
| --- | --- | --- |
| 0A — baseline and controls | None | Baseline manifest, original-input hashes, retrievable evidence index, frozen test inventory and benchmark policy. Current v1.13 Gate 0 is a separate native execution prerequisite. Historical archives retain explicit missing status; current-run claims require their own complete evidence. |
| 0B — census and closure | Current Gate 0; R6 before/after comparison for stub registration | Evaluated operators and flags; target handlers/lowerings, primitives/imports/traps/stores; function/module graph; external cold-start trace; initializer dependency order; no unresolved reachable required edge under the closure contract. |
| 0C — representation and engine foundations | 0A | Engine/version/features; layout fixtures; debugger frame maps; exact linked C memory/table ownership, per-Worker stack and initialization maps; materialized profile binaries. Independent fixtures and specified rejection cases pass. |
| 0D — integrated control and concurrency | 0C | One hand-built harness combines moving-root restoration, competing GC requests, interruptible unfinished I/O, nested callbacks, late Workers, lazy installation and EH crossing C helpers. Deterministic and seeded schedules meet progress/resource limits. |
| 0E — ABI decision/correctness | B correctness prerequisites | Record the B engineering choice and its reviewed correctness basis: arguments, result ownership, frames, cleanup and debugger policy. Comparative measurements are deferred; they do not block B implementation. |
| 0F — acceptance | 0B–0E | All Stage 0 IDs, standing controls, outline exit criteria, source/test/artifact hashes and negative controls are present; review records actual evidence scope. Unresolved mandatory work blocks Stage 1. |

## Baseline qualification and R6

The native baseline protects existing CCL behavior when shared compiler work begins. The project reference is macOS; U1 v1.13 uses the x86-64 Darwin native target on this Intel Mac. The Wasm target runs in its engine and does not depend on a native operating-system ABI. No container setup is part of this plan.

`baseline.json` pins source, the Darwin bootstrap archive and ccl-tests. The [macOS native runner](../../../tests/wasm/native-baseline/README.md) builds the unchanged kernel, performs two clean rebuilds from the same bootstrap at the same path, starts each rebuilt image and runs the pinned test corpus. Raw FASL repeatability is recorded separately. The user [retired S0-LL08-c](second-mac-decision.md) on 13 September; a second Mac is not required.

Before a shared compiler edit, capture an immutable unchanged-source corpus containing representative direct/dynamic calls, closures, conditions, multiple values, numeric and target-specific lowering cases, together with the whole native build output. After the edit, rebuild and compare under acceptance section 2. Accompany each intentionally modified shared compiler FASL with a narrow change-to-artifact explanation and unchanged-input native output tests. Native execution is scoped to the macOS reference. Other upstream target source remains protected; no equivalence claim is made for an unexecuted target.

## Proof implementation order

### Alternating deliverables — 13 September 2026

Following the user-supplied twenty-second Claude review and the user's instruction
to continue through the next step, interleave census work with independently
closable Stage 0 records. Keep one deliverable and one compact packet per commit;
independent review and project acceptance remain separate from execution.

1. [S0-LL02-a](inventory-control.md), the production-gate missing-inventory control, is accepted after Claude's twenty-third audit and the user's explicit decision.
2. Return to the census: establish a target macro environment from source, with
   explicit expander/helper identities and gaps before claiming target qualification.
   The [complete observed expansion routing](source-expanders.md) now rebuilds
   all 293 hook invocations from source, extending the reviewed first slice.
   The [numeric/layout helper slice](target-helpers.md) now repairs inherited
   host-width assumptions for eight numeric probes and records 40 helper calls
   in the genuine traversal. It supplies two of the 68 original helper bodies
   in three private macro entries; nonconstant type facts and transitive paths
   are still unqualified. Remaining helpers, computed calls, object references
   and the five source boundary stops remain explicit.
3. The [B desk-decision record](abi-decision.md) is accepted after Claude's twenty-sixth
   audit and the user's explicit decision. The subsequent helper slice above is
   reviewed without defect by Claude's twenty-seventh audit.
4. [S0-LL03-a](evidence-kind-control.md) now executes the evidence-kind standing
   control: two complete synthetic inputs pass and 22 defective inputs reject
   through the unchanged production gate. Accepted after Claude's twenty-eighth
   audit and the user's explicit decision.
5. The [declared-type helper slice](target-types.md) now supplies source type-query
   bodies and compound target translation within the private EQL macro. Fifteen
   probes and the genuine file trace expose and repair unsafe EQ decisions for
   declared boxed integers while respecting declaration policy. Claude's
   twenty-ninth audit reviewed it without defect; general type inference and
   other helpers remain open.
6. [S0-LL01-b](child-command-control.md) now exercises the production native
   aggregate with real failed, killed and timed-out children under synthetic
   command stimuli. One complete workflow passes and ten controls reject;
   Claude's thirtieth audit reviewed it without defect; the user has accepted it.
7. The [TYPEP helper slice](target-predicates.md) corrects host membership answers
   for target fixnums/bignums, supplies the source optimizer body and preserves
   the native ctype guard. Twenty-two front-end probes, five native controls and
   22 checker controls pass. Claude's thirty-first audit reviewed it without defect;
   aliases, native class objects and wider inference remain open.
8. [S0-LL02-b](behavioral-control.md) now executes an escaping mutable closure,
   all six values and nested cleanup through normal and exceptional Wasm exits.
   Five positive calls and five semantic mutants pass; accepted by the user after
   Claude's thirty-second audit.
9. The [DEFTYPE order slice](target-aliases.md) expands source-defined aliases
   before target membership and canonicalization. Sixteen constant probes and
   five recursive optimizer probes expose and correct inherited wrong answers;
   five native and twenty checker controls reject. Claude's thirty-third audit
   reviewed it without defect.
10. [S0-LL01-a](initializer-control.md) now executes early/middle/late initializer
    exceptions in the Stage 0 Wasm harness. Diagnostic continuation preserves the
    first error, blocks dependents and withholds ready publication; a missing
    module refuses before initialization. One complete, eight refused bootstraps
    and four rejected loader mutations pass. Claude's thirty-fourth audit reviewed
    it without defect; the user explicitly accepted S0-LL01-a on 13 September.
11. The [native object serialization witness](target-objects.md) joins the actual
    IOBLOCK class cell and registered RESTART wrapper to U1's symbolic FASL paths.
    Five native registry roundtrips and four negative inputs pass; seven data
    files reproduce and sixteen checker controls reject. This establishes the
    native serialization behavior, reviewed without defect by Claude's
    thirty-fifth audit. Target registry materialization remains open. When that
    work is scheduled, add an explicit required census node for RESTART wrapper
    contents, supplied by the target class system at load time. The serialized
    RESTART key alone must not mark that node implemented.
12. [S0-LL22-a](artifact-identity-control.md) now executes artifact identity and
    role checks through the unchanged production gate: two complete synthetic
    builds pass and 36 defective records reject, including different installed
    binaries sharing a template. Claude's thirty-sixth audit found no defect;
    the user accepted the enforcement scope on 14 September. Production-policy
    enhancement is separately authorized.
13. The [architecture dispatch slice](target-dispatch.md) now supplies four
    private U1 lookup bodies and joins both real architecture-macro events to
    the current target registry. Nine transition probes agree with the unchanged
    native dispatcher; four native and 25 checker controls reject. No new
    semantic defect found, no widening edge replaced and no gate credit.
    Claude's thirty-seventh audit reviewed it without defect. Next return to a remaining standing control,
    then to the other census helpers, five boundary contracts and broader source
    traversal.

The B desk record's actual inventory prerequisites are the reviewed ABI/runtime
records; S0-ENGINE-a is not a prerequisite of S0-ABI-selection. Engine qualification
remains a separate mandatory slot. The other non-census work also includes the
final S0-CONTRACTS-a join, which stays last. Scheduling a control does not waive
full source closure or authorize functional shared compiler changes.

### Remaining work — user direction, 12 September 2026

The five steps below supersede the historical implementation order that follows. Work in small commits with one deliverable each. Reuse the reviewed r7 logs, graph and Terminal r2 trace; do not rebuild or rehash their unchanged prerequisite archive for each change. The [standing rules](../../../CLAUDE.md) now require verification scoped to changed work and its dependencies. Preserve R6, original failures and independent review.

1. Complete the startup census under S0-LL15-b/c. The [joined projection](joined-census.md) now preserves the retained input identities, effects and evaluated metadata in the exchange format, with specific omission controls and the reviewed dyld classification. The [richer collector](rich-census.md) now supplies actual expander, installation, materialization and initializer identities, native instruction operands and inspection of the exact traced image. The [initializer integration](initializer-joins.md) now places exact callees, returned values and per-process effect boundaries in that graph. The [native emission joins](native-emission-joins.md) add observed function/template/handler dependencies and parameterized subprimitive operands. The [early-boot witness](boot-observation.md) now records the boot-image subprocess separately; Claude has reviewed its execution scope, but all 133 cold thunks lack runtime source notes. The [xload insertion witness](cold-initializer-origins.md) now supplies module origins for all 133, with 131 source contexts and two null ranges. Claude's seventeenth audit reviewed that witness. The [boot integration](boot-integration.md) now places the execution, binding histories and origin edges in the exchange graph, reviewed by Claude's eighteenth audit; its historical-scenario obligations remain open. The [wrapper follow-up](boot-wrappers.md) resolves the 1,059 previously opaque macro/special values, reviewed by Claude's nineteenth audit. The [seed revision](startup-seed-revision.md) addresses the kernel entry proposal with actual callback, builtin and method identities, approved by Claude's twentieth audit for the native profile; save/restore callback equality remains open. Its diagnostic confirms that removing only the two largest membership edges still masks every seed omission. Replace membership widening with source traversal and bounded calls before closure. Complete target source traversal and the other lowering/import/store classes, and review the seed set and conservative call bounds. Consult the [attempt-1 reference survey](../history/attempt1-reference.md) for the seeds, initialization cycle, conditional load and dynamic-call families that failed there; it is reference, not evidence. Do not infer missing observations from printed previews or treat image construction as initializer execution.
2. S0-LL08-a's [registration/target-state proof](stub-registration.md), including R6, is accepted at 02ff713d. Extend static reachability beyond its fourteen-form fixture using that registration. All formal LL15 prerequisites are accepted; full source closure is still work to perform. The reviewed [first driver](source-traversal.md) accounts for every top-level form of `lib/dumplisp.lisp`. The [description extension](target-descriptions.md) now captures seven definitions, two top-level initializer bodies and four deferred load-time initializers; five native-boundary stops remain. Its eight D1-derived subtype rows and eight explicit boundary obligations preserve the distinction between data layout, native-only mechanisms and required startup services. Next qualify the inherited macro environment, implement or refine the boundary replacements in isolated fixtures, and bound the restore callback calls before expanding the source inventory. No existing widening edge is removed by this partial capture. General top-level macros, includes and conditional top-level forms still need traversal support and controls. All source experiments remain in disposable pristine U1 copies; implementation starts from a clean baseline.
3. Complete the unblocked standing controls, engine matrix and remaining isolated hand-built fixtures: LL07-a, LL13-b, LL19-a, both LL21-c variants and LL15-a. Keep each deliverable and its validation separate.
4. S0-ABI-selection is accepted at 8e7a4221, using the dated engineering rationale and reviewed correctness evidence. No timing trial or benchmark-selection claim was added.
5. Complete S0-CONTRACTS-a after its constituent evidence is available.

The proposed experimental B pass-2 slice is a separate scope decision: disposable U1, actual front-end output, native-result comparison, and adversarial review before any merge into the implementation checkout. The current exception authorizes observation only; this execution order does not itself amend the functional-compiler restriction.

The [13 September bootstrap design review](bootstrap-design-review.md) makes the integration priorities explicit: establish phase prerequisites and the early-to-full error-service transition; extend the first generated B slice through closures, dynamic binding, multiple values and image identity; then exercise the compiler-to-bootstrap path in a fresh process. Coherent eager bootstrap bundles are a proposed starting configuration, with production packaging still open. The review preserves existing gate criteria and the B decision; the archived survey supplies leads to verify against U1.

### Historical implementation order

1. Run the limited `PROBE-*` layout, materialization and late-Worker probes to establish the execution/reporting path. Do not map their passing results to full LL slices.
2. Implement S0-LL13-c and S0-LL19-b with the actual freestanding C build, link maps, isolated C stacks and exceptional restoration. Record allowed helper imports and check the final Wasm, including initialization writes.
3. Build S0-LL20-a/b/c around that same harness. Use barriers/latches for exact schedules; include collector CAS loss, release/re-admission, child registration, completion versus interrupt/rearm, cancellation acknowledgement and descriptor lifetime. Require real object movement and rereading updated root slots.
4. Prove logical debugger frames under S0-LL23-b before freezing D3: moved roots, lexical/source identities, explicit unavailable values, nested inspection and EH restoration.
5. Retain the reviewed C/C4/B correctness corpus and implement the selected B protocol through generated code. Comparative timing is deferred under the 12 September engineering decision.
6. Instrument the qualified native compiler for S0-LL15-b/c. Resolve unknown graph edges conservatively, retain the external trace and justify every unobserved dependency.

The integrated harness must also define fatal-owner failure: an unexpected trap, dead Worker or expired rendezvous while holding collection ownership fails the **whole proof process**. A supervisor records the first failure and terminates remaining participants; it must not clear `gc_gen` and resume potentially inconsistent heap access. Recovery from a crashed collector is not a Stage 0 capability claim.

Step 2 now has an [executable boundary fixture](../../../tests/wasm/stage0/runtime-boundary/README.md) and retained execution results linked from [current status](../STATUS.md). Its result-region and restart rules are explicit fixture contracts; they do not select D3 or discharge the integrated step 3.

Step 3 now has an [integrated executable fixture](../../../tests/wasm/stage0/integrated-runtime/README.md) for S0-LL20-a/b/c. The requested hand-built moving-GC, concurrency and I/O work has executed successfully, including its seeded schedules and rejection controls. See [execution scope and implementer review](integrated-runtime.md). This does not close the remaining 0C contracts/engine matrix, select D3, supply a native census or constitute full Stage 0 acceptance.

## Initial measurement policy

`benchmarks.json` version 3 records the B engineering choice and defers comparative timing. The original numerical comparison parameters remain available for optional future use; dedicated-host correctness/progress limits remain mandatory at their stated scope. Old/new policy hashes and the dated rationale are retained. No timing threshold is claimed satisfied by this choice.

The 0E experiment review occurs after at most 20 engineer-days of ABI-specific work. This is a planning checkpoint; it does not pass D3 when required work is incomplete. If incomplete, record remaining work and revise the work budget explicitly while leaving Stage 0 incomplete. The three-to-six engineer-year estimate remains an unvalidated planning assumption until 0B–0E and the first generated Stage 1 slice provide actual velocity.

The macOS reference has now executed two clean builds successfully: 21,843 eligible release-era tests pass in each, and all 164 FASLs match byte-for-byte. See the [native summary](../evidence/native-baseline-summary.json). The 75 upstream-disabled tests are listed with notes. A separate [current-head diagnostic](../evidence/native-current-tests-diagnostic.json) retains three post-v1.13 failures; it is not relabeled as passing. Same-host project acceptance is recorded in [the decision](project-acceptance.md); second-Mac reproduction was retired by the [13 September decision](second-mac-decision.md).

The logical-frame and C/C4/B correctness records are accepted within the [seven-record and fourth-audit decisions](project-acceptance.md). The isolated [measurement fixture](abi-measurements.md) and its S0-LL21-a identity-publication record are reviewed, with LL21-a accepted by the user after correction of the misattributed authorization. [B is chosen](abi-choice.md) for simplicity; comparative timing and proposed comparison instrumentation are deferred. Separately authorized [reversible native observation](native-census.md) has executed from clean U1. S0-LL08-b is accepted. Claude's seventh audit reviewed the [dependency extension](native-dependencies.md) and trace derivative without finding a defect, at their diagnostic scope. The dyld trace classification is complete. The newer compiler/loader identity collection supplies observations for resolving the retained dynamic calls and global binding versions; qualify their bounds and seeds, and complete the lowering/initializer joins. Functional shared compiler changes still require an authorized author; observed images and patched source never become implementation inputs.

## Product-risk work alongside ABI correctness

The [scale, startup and granularity plan](product-risk-plan.md) makes the unmeasured product risks explicit. D3 recommendations must state their module-granularity and code-installation assumptions and test sensitivity to them. The native census and an authorized compiler spike should proceed alongside C/C4/B work. The user has removed H(G) from all scheduled gates; it remains only a possible future enhancement.

## Evidence compatibility

New acceptance producers use the [version 2 binding contract](../contracts/evidence-binding.md). Retain each execution’s original inventory snapshot and bind its test entry and transitive prerequisites, excluding only documented review/status bookkeeping. Add unrelated IDs without changing the inventory version; change that version only when global compatibility must be invalidated. Contract and policy changes update the affected semantic entry. A separate verified format upgrade can preserve compatible legacy evidence without claiming execution. Missing results and independent acceptance remain required.


### Immediate work — user direction, 14 September 2026

S0-LL22-a, S0-LL23-a and S0-LL24-a are accepted after their independent reviews
and the user's explicit decisions. The production artifact policy is reviewed
without defect. Stage 0 has 37 accepted and eleven missing required slots.

Resume census helper qualification with the SETF expander registry and its
computed calls in the image-restore traversal, then the five source-boundary
contracts and broader traversal. Continue the alternating remaining Stage 0
work. LL22-b remains a separate missing R6 control. Existing fixtures do not
discharge full census closure or authorize functional shared compiler changes.


The [SETF lookup witness](target-setf.md) now joins all five observed lookups to
their branches and four named setters to U1 declarations. No callable expander
runs in the restore file. Nine separate target-context probes agree with native
SETF; five native and 25 checker controls reject. Seven captured definitions and
five source-boundary stops remain. Independent review is pending; no census gate
credit. Next take S0-LL22-b, the remaining R6 standing control, then return to
census helpers and the five boundary replacements under the alternating plan.
