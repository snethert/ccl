# Stage 0 execution plan

This plan decomposes the existing Stage 0 exit criteria. No subgate completion removes continuing regressions or later compiler-generated obligations. `inventory.json` carries the exact expected IDs; `obligations.json` is generated from the register. Status belongs in `../STATUS.md` and identified execution records, not inferred from file existence.

| Subgate | Prerequisites | Concrete deliverable and exit observation |
| --- | --- | --- |
| 0A — baseline and controls | None | Baseline manifest, original-input hashes, retrievable evidence index, frozen test inventory and benchmark policy. Current v1.13 Gate 0 is a separate native execution prerequisite. Historical archives retain explicit missing status; current-run claims require their own complete evidence. |
| 0B — census and closure | Current Gate 0; R6 before/after comparison for stub registration | Evaluated operators and flags; target handlers/lowerings, primitives/imports/traps/stores; function/module graph; external cold-start trace; initializer dependency order; no unresolved reachable required edge under the closure contract. |
| 0C — representation and engine foundations | 0A | Engine/version/features; layout fixtures; debugger frame maps; exact linked C memory/table ownership, per-Worker stack and initialization maps; materialized profile binaries. Independent fixtures and specified rejection cases pass. |
| 0D — integrated control and concurrency | 0C | One hand-built harness combines moving-root restoration, competing GC requests, interruptible unfinished I/O, nested callbacks, late Workers, lazy installation and EH crossing C helpers. Deterministic and seeded schedules meet progress/resource limits. |
| 0E — ABI selection | 0C/0D correctness prerequisites | C/C4/B correctness, then their measurements; H(G) correctness, then comparisons with the same G. Contract includes arguments, result-region lifetime, frames, cleanup and debugger policy. Census distributions refine workload weights before selection measurements are frozen. |
| 0F — acceptance | 0B–0E and U1 second-host reproduction S0-LL08-c | All Stage 0 IDs, standing controls, outline exit criteria, source/test/artifact hashes and negative controls are present; review records actual evidence scope. Unresolved mandatory work blocks Stage 1. |

## Baseline qualification and R6

The native baseline protects existing CCL behavior when shared compiler work begins. The project reference is macOS; U1 v1.13 uses the x86-64 Darwin native target on this Intel Mac. The Wasm target runs in its engine and does not depend on a native operating-system ABI. No container setup is part of this plan.

`baseline.json` pins source, the Darwin bootstrap archive and ccl-tests. The [macOS native runner](../../../tests/wasm/native-baseline/README.md) builds the unchanged kernel, performs two clean rebuilds from the same bootstrap at the same path, starts each rebuilt image and runs the pinned test corpus. Raw FASL repeatability is recorded separately. S0-LL08-c repeats this target on a second Mac; it does not require a second operating system.

Before a shared compiler edit, capture an immutable unchanged-source corpus containing representative direct/dynamic calls, closures, conditions, multiple values, numeric and target-specific lowering cases, together with the whole native build output. After the edit, rebuild and compare under acceptance section 2. Accompany each intentionally modified shared compiler FASL with a narrow change-to-artifact explanation and unchanged-input native output tests. Native execution is scoped to the macOS reference. Other upstream target source remains protected; no equivalence claim is made for an unexecuted target.

## Proof implementation order

1. Run the limited `PROBE-*` layout, materialization and late-Worker probes to establish the execution/reporting path. Do not map their passing results to full LL slices.
2. Implement S0-LL13-c and S0-LL19-b with the actual freestanding C build, link maps, isolated C stacks and exceptional restoration. Record allowed helper imports and check the final Wasm, including initialization writes.
3. Build S0-LL20-a/b/c around that same harness. Use barriers/latches for exact schedules; include collector CAS loss, release/re-admission, child registration, completion versus interrupt/rearm, cancellation acknowledgement and descriptor lifetime. Require real object movement and rereading updated root slots.
4. Prove logical debugger frames under S0-LL23-b before freezing D3: moved roots, lexical/source identities, explicit unavailable values, nested inspection and EH restoration.
5. Implement all generic ABI candidates through one parameterized test corpus. Select no ABI from the initial probes. Freeze workload weights and the benchmark policy digest before selection measurements, then evaluate H(G) in the specified order.
6. Instrument the qualified native compiler for S0-LL15-b/c. Resolve unknown graph edges conservatively, retain the external trace and justify every unobserved dependency.

The integrated harness must also define fatal-owner failure: an unexpected trap, dead Worker or expired rendezvous while holding collection ownership fails the **whole proof process**. A supervisor records the first failure and terminates remaining participants; it must not clear `gc_gen` and resume potentially inconsistent heap access. Recovery from a crashed collector is not a Stage 0 capability claim.

Step 2 now has an [executable boundary fixture](../../../tests/wasm/stage0/runtime-boundary/README.md) and retained execution results linked from [current status](../STATUS.md). Its result-region and restart rules are explicit fixture contracts; they do not select D3 or discharge the integrated step 3.

Step 3 now has an [integrated executable fixture](../../../tests/wasm/stage0/integrated-runtime/README.md) for S0-LL20-a/b/c. The requested hand-built moving-GC, concurrency and I/O work has executed successfully, including its seeded schedules and rejection controls. See [execution scope and implementer review](integrated-runtime.md). This does not close the remaining 0C contracts/engine matrix, select D3, supply a native census or constitute full Stage 0 acceptance.

## Initial measurement policy

`benchmarks.json` sets the initial selection thresholds and dedicated-host acceptance limits. They are engineering targets, not achieved measurements or browser scheduling guarantees. Policy revisions require a dated rationale, old/new hashes and rerunning affected measurements. Do not relax a limit after seeing an unfavorable candidate without recording the scope change.

The 0E experiment review occurs after at most 20 engineer-days of ABI-specific work. This is a planning checkpoint, not a timeout that passes D3 or permission to skip H. If incomplete, record remaining work and revise the work budget explicitly while leaving Stage 0 incomplete. The three-to-six engineer-year estimate remains an unvalidated planning assumption until 0B–0E and the first generated Stage 1 slice provide actual velocity.

The macOS reference has now executed two clean builds successfully: 21,843 eligible release-era tests pass in each, and all 164 FASLs match byte-for-byte. See the [native summary](../evidence/native-baseline-summary.json). The 75 upstream-disabled tests are listed with notes. A separate [current-head diagnostic](../evidence/native-current-tests-diagnostic.json) retains three post-v1.13 failures; it is not relabeled as passing. Second-Mac reproduction and independent acceptance remain outstanding.

The logical-frame step now has an [executable fixture](../../../tests/wasm/stage0/debug-frames/README.md) and [retained scope record](debug-frames.md). It links the reviewed runtime unchanged. Independent review of the new frame work is pending. Next, implement C/C4/B correctness through one parameterized corpus, including this frame/root/cleanup ownership contract, before measuring or selecting an ABI. Native census instrumentation requires an author authorized to modify shared compiler source under the standing rules.
