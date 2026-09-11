# Integrated runtime execution and implementer review — 2026-09-11

The requested hand-built moving-GC, concurrency and interruptible-I/O work is implemented and executed. The externally reviewed run **INTEGRATED-RUNTIME-r10** passes S0-LL20-a/b/c and freshly reruns S0-LL13-c/S0-LL19-b. See the [runner and contracts](../../../tests/wasm/stage0/integrated-runtime/README.md), [machine summary](../evidence/integrated-runtime-summary.json) and [retained-pack index](../evidence/index.json).

| Slice | Deterministic positive cases | Rejection controls | Observed behavior |
| --- | --- | --- | --- |
| S0-LL20-a | 3 | 2 | Zero/one/six values across suspended nested frames, real object movement, C/emitted root reload and admitted code installation. |
| S0-LL20-b | 14 | 8 | Competing collectors, owner release/re-entry, parity wrap, admission, final membership rescan, handoff roots, allocation recheck, interrupted I/O and completion/cancellation races. |
| S0-LL20-c | 5 | 4 | Nested debugger requests/interrupt routing, repeated collection with live C frames, nonlocal cleanup, stable payload lifetime, acknowledged reclamation and stale host publication rejection. |

The runner additionally executes 1,000 seeds with a concurrently polling mutator. The recorded p99 safepoint latency is **0.041 ms**, the maximum is **0.626 ms**, and the longest collection rendezvous is **4.481 ms**. All schedules meet the 5-second limit. These are measurements from the recorded macOS/Node host and instrumented fixture; they do not qualify browser scheduling or select an ABI.

## Reproduce and inspect

From the repository root, use the runner command in its README. Output must be a new directory outside the checkout. Each pack contains `results.json`, source snapshots, the exact inventory and benchmark policy, toolchain/host identity, build commands, objects, final modules, link metadata, deterministic cases, raw seeded traces and quarantined mutants.

For the current execution, extract DEBUG-FRAMES-r3 from the [index](../evidence/index.json) into an empty directory and run `doc/WASM/tools/gate.py` with the current inventory and the extracted `prerequisites/results.json`. Historical r10 must use its own archived inventory; its original binding is not current. The expected full-Stage-0 result is **BLOCKED**, exit 2, for remaining results and acceptance reviews. The [retained gate assessment](../evidence/integrated-runtime-gate-result.json) verifies the actual archived artifacts; documentation generation is not an acceptance substitute.

## Implementer review

The points below are implementer verification. [Claude’s external r8 audit and its dispositions](claude-review.md) are recorded separately. Claude’s second audit re-executed r10 byte-identically and found no further defect; acceptance remains a separate project decision. The logical-frame proof freshly reruns the unchanged integrated prerequisites against the updated inventory; its new code has not received that audit.

- The collector copies objects and scans actual published root chains, including live C stack records, emitted binding frames and complete result regions. Tests read the relocated graph, preserve cycles/aliases, inspect rewritten roots and require old-space poison. Separate C and Wasm stale-reference mutants fail.
- GC ownership is acquired by CAS. A loser cannot change parity. Former owners and losing requesters retry admission when a new collection races with wake-up. Registration precedes child execution; final membership rescan includes a handoff root after its parent relinquishes it. An unpublished-child admission is rejected.
- Stable host byte payloads are outside the moved heap. Interrupts preserve unrelated pending bits, wake the actual current wait, and cannot erase durable terminal outcomes. The nested request uses a separate descriptor while its parent's request remains owned.
- A final host wake after result consumption/reuse was reproduced in [failed run r3](../evidence/runs/2026-09-11-integrated-r3.zip). Generation-guarded 64-bit wake publication fixes it. A parent-versus-nested wait routing defect was reproduced in [failed run r6](../evidence/runs/2026-09-11-integrated-r6.zip); the explicit active-request pointer fixes it. Both original failures and corresponding failing mutants are retained.
- Claude identified an idle-state defect, reproduced in [failed r9](../evidence/runs/2026-09-11-integrated-r9.zip). The fixed exceptional path parks, and retirement first admits. A real collection completes while the exceptional-return Worker is idle; the omitted-park mutant reproduces the failed world. Nonlocal exit restores the C stack pointer and emitted root/binding/stack/active-request checkpoints, performs cleanup once, and retains the abandoned request. Reclamation requires a subsequent completed collection and a terminal host outcome. It cannot run twice or permit a stale host write.
- A collector trap fails the whole proof. The supervisor terminates participants while retaining the odd marker and failed owner in the failure snapshot. It never clears ownership to manufacture recovery.

This work does not implement production CCL object coverage, generational/weak-object collection, the complete condition system, browser/JSPI profiles, D3 candidate selection, native compiler instrumentation or a self-hosted compiler. Those remain on the [Stage 0 ledger](../STATUS.md). Existing native implementation source is unchanged.
