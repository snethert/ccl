# Stage 0 execution plan

This plan decomposes the existing Stage 0 exit criteria. No subgate completion removes continuing regressions or later compiler-generated obligations. `inventory.json` carries the exact expected IDs; `obligations.json` is generated from the register. Status belongs in `../STATUS.md` and identified execution records, not inferred from file existence.

| Subgate | Prerequisites | Concrete deliverable and exit observation |
| --- | --- | --- |
| 0A — baseline and controls | None | Baseline manifest, original-input hashes, retrievable evidence index, frozen test inventory and benchmark policy. Current v1.13 Gate 0 is a separate native execution prerequisite. Historical archives retain explicit missing status; current-run claims require their own complete evidence. |
| 0B — census and closure | Current Gate 0; R6 before/after comparison for stub registration | Evaluated operators and flags; target handlers/lowerings, primitives/imports/traps/stores; function/module graph; external cold-start trace; initializer dependency order; no unresolved reachable required edge under the closure contract. |
| 0C — representation and engine foundations | 0A | Engine/version/features; layout fixtures; debugger frame maps; exact linked C memory/table ownership, per-Worker stack and initialization maps; materialized profile binaries. Independent fixtures and specified rejection cases pass. |
| 0D — integrated control and concurrency | 0C | One hand-built harness combines moving-root restoration, competing GC requests, interruptible unfinished I/O, nested callbacks, late Workers, lazy installation and EH crossing C helpers. Deterministic and seeded schedules meet progress/resource limits. |
| 0E — ABI decision/correctness | B correctness prerequisites | Record the B engineering choice and its reviewed correctness basis: arguments, result ownership, frames, cleanup and debugger policy. Comparative measurements are deferred; they do not block B implementation. |
| 0F — acceptance | 0B–0E and U1 second-host reproduction S0-LL08-c | All Stage 0 IDs, standing controls, outline exit criteria, source/test/artifact hashes and negative controls are present; review records actual evidence scope. Unresolved mandatory work blocks Stage 1. |

## Baseline qualification and R6

The native baseline protects existing CCL behavior when shared compiler work begins. The project reference is macOS; U1 v1.13 uses the x86-64 Darwin native target on this Intel Mac. The Wasm target runs in its engine and does not depend on a native operating-system ABI. No container setup is part of this plan.

`baseline.json` pins source, the Darwin bootstrap archive and ccl-tests. The [macOS native runner](../../../tests/wasm/native-baseline/README.md) builds the unchanged kernel, performs two clean rebuilds from the same bootstrap at the same path, starts each rebuilt image and runs the pinned test corpus. Raw FASL repeatability is recorded separately. S0-LL08-c repeats this target on a second Mac; it does not require a second operating system.

Before a shared compiler edit, capture an immutable unchanged-source corpus containing representative direct/dynamic calls, closures, conditions, multiple values, numeric and target-specific lowering cases, together with the whole native build output. After the edit, rebuild and compare under acceptance section 2. Accompany each intentionally modified shared compiler FASL with a narrow change-to-artifact explanation and unchanged-input native output tests. Native execution is scoped to the macOS reference. Other upstream target source remains protected; no equivalence claim is made for an unexecuted target.

## Proof implementation order

### Remaining work — user direction, 12 September 2026

The first six steps below supersede the historical implementation order that follows. Work in small commits with one deliverable each. Reuse the reviewed r7 logs, graph and Terminal r2 trace; do not rebuild or rehash their unchanged prerequisite archive for each change. The [standing rules](../../../CLAUDE.md) now require verification scoped to changed work and its dependencies. Preserve R6, original failures and independent review.

1. Complete the startup census under S0-LL15-b/c. The [joined projection](joined-census.md) now preserves the retained input identities, effects and evaluated metadata in the exchange format, with specific omission controls and the reviewed dyld classification. It remains unqualified: extend observation for complete expansion/installation identities, semantic initializer state/completion and evaluated lowering/import/store joins, then review the seed set and conservative call bounds. Do not infer those observations from printed previews or emission logs.
2. S0-LL08-a's [registration/target-state proof](stub-registration.md), including R6, is accepted at 02ff713d. Extend static reachability beyond its fourteen-form fixture using that registration. All formal LL15 prerequisites are accepted; full source closure is still work to perform.
3. Complete the unblocked standing controls, engine matrix and remaining isolated hand-built fixtures: LL07-a, LL13-b, LL19-a, both LL21-c variants and LL15-a. Keep each deliverable and its validation separate.
4. Produce the S0-ABI-selection desk-decision record for B, using the existing dated engineering rationale and reviewed correctness evidence. No new timing trials or benchmark-selection claim.
5. Reproduce S0-LL08-c on a second Mac when the user supplies one. This does not prevent the other work.
6. Complete S0-CONTRACTS-a after its constituent evidence is available.

The proposed experimental B pass-2 slice is a separate scope decision: disposable U1, actual front-end output, native-result comparison, and adversarial review before any merge into the implementation checkout. The current exception authorizes observation only; this execution order does not itself amend the functional-compiler restriction.

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

The macOS reference has now executed two clean builds successfully: 21,843 eligible release-era tests pass in each, and all 164 FASLs match byte-for-byte. See the [native summary](../evidence/native-baseline-summary.json). The 75 upstream-disabled tests are listed with notes. A separate [current-head diagnostic](../evidence/native-current-tests-diagnostic.json) retains three post-v1.13 failures; it is not relabeled as passing. Same-host project acceptance is recorded in [the decision](project-acceptance.md); second-Mac reproduction remains outstanding.

The logical-frame and C/C4/B correctness records are accepted within the [seven-record and fourth-audit decisions](project-acceptance.md). The isolated [measurement fixture](abi-measurements.md) and its S0-LL21-a identity-publication record are reviewed, with LL21-a accepted by the user after correction of the misattributed authorization. [B is chosen](abi-choice.md) for simplicity; comparative timing and proposed comparison instrumentation are deferred. Separately authorized [reversible native observation](native-census.md) has executed from clean U1. S0-LL08-b is accepted. Claude's seventh audit reviewed the [dependency extension](native-dependencies.md) and trace derivative without finding a defect, at their diagnostic scope. Next: conservatively resolve the remaining 1,729 dynamic calls and global binding versions, qualify seeds, and complete lowering/initializer joins and dyld trace classification. Functional shared compiler changes still require an authorized author; observed images and patched source never become implementation inputs.

## Product-risk work alongside ABI correctness

The [scale, startup and granularity plan](product-risk-plan.md) makes the unmeasured product risks explicit. D3 recommendations must state their module-granularity and code-installation assumptions and test sensitivity to them. The native census and an authorized compiler spike should proceed alongside C/C4/B work. The user has removed H(G) from all scheduled gates; it remains only a possible future enhancement.

## Evidence compatibility

New acceptance producers use the [version 2 binding contract](../contracts/evidence-binding.md). Retain each execution’s original inventory snapshot and bind its test entry and transitive prerequisites, excluding only documented review/status bookkeeping. Add unrelated IDs without changing the inventory version; change that version only when global compatibility must be invalidated. Contract and policy changes update the affected semantic entry. A separate verified format upgrade can preserve compatible legacy evidence without claiming execution. Missing results and independent acceptance remain required.
