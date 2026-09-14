# Initializer failure control — 13 September 2026

Status: executed; independent review and project acceptance pending.
`STANDING-INITIALIZER-CONTROL-R1` is retained in
`2026-09-13-initializer-control-r1` through the
[evidence index](../evidence/index.json). This is S0-LL01-a/control, following the
user's acceptance of S0-LL01-b and S0-LL02-b.

The [Stage 0 harness](../../../tests/wasm/stage0/initializer-control/bootstrap.mjs)
runs nine required initializers in three hand-built Wasm modules. Each module
holds a three-step chain; the three chain roots are independent. Wasm records
entry, effects, call order and completion in linear memory. An injected failure
throws a real Wasm exception after the effect but before completion. The loader
records its module, initializer ID, index and exception payload.

Normal execution stops at the first failed initializer. Diagnostic execution
retains failures, blocks their dependent steps and continues independent chains.
It preserves the original first failure even when another chain fails later.
Only an entirely completed, error-free run may publish the ready artifact.
Partial memory effects remain observable for diagnosis; no rollback is claimed.

| Scenario | Executed / completed initializers | Result |
| --- | --- | --- |
| Complete | 9 / 9 | One ready artifact; aggregate passes |
| Early failure at 0 | 1 / 0 | Exact first error; aggregate fails |
| Middle failure at 4 | 5 / 4 | Exact first error; aggregate fails |
| Late failure at 8 | 9 / 8 | Exact first error; aggregate fails |
| Diagnostic early failure | 7 / 6 | Two dependent steps blocked; aggregate fails |
| Diagnostic middle failure | 8 / 7 | One dependent step blocked; aggregate fails |
| Diagnostic late failure | 9 / 8 | Aggregate fails |
| Diagnostic failures at 0 and 4 | 6 / 4 | Both errors retained, first remains 0; three blocked |
| Missing required module | 0 / 0 | Actual missing-file read rejects before any initializer |

Every negative scenario withholds the ready artifact. The independent literal
oracle checks all step records, physical memory writes and call order, all errors,
first error, return values and publication bytes. Module preflight completes
before initialization. The omission case directs the types-module fetch to an
absent filename and exercises the actual filesystem ENOENT path; module bytes
remain retained as control input.

Four separately quarantined loader changes are rejected by that unchanged oracle:
accepting a late partial bootstrap; overwriting the first error; publishing before
checking completion; and labeling a failed step completed. The premature-publication
mutant still returns FAIL, demonstrating that aggregate status alone is insufficient.
Engine errors, build failures and unexpected child exits fail the producer and do
not count as successful controls.

The final producer and fresh replay pass. All three modules and thirteen original
observation records are byte-identical, together with their WAT, manifest, configs,
mutated loader sources and publication artifacts. Eight direct source pins and
the production slot gate pass. The slot gate is blocked only for review/acceptance.
Preparatory successful runs are retained: the first preceded an explicit case-list
bound and documentation correction; the second used an injected ENOENT instead of
the final actual missing-file read. No unexpected execution failure occurred.

This is a new isolated Stage 0 harness with real Wasm execution. It qualifies no
CCL image restore, generated compiler code, arbitrary manifest/schema behavior,
collector, threads, initializer timeout, recovery restart or future production
Stage 1 loader. LL01-b separately covers required-child outcomes. No shared
compiler, upstream kernel, production gate or existing fixture changed.

The scoped ledger is **33 accepted, 14 missing and one unreviewed of 48**. The new
slot awaits review and acceptance; earlier accepted records remain unchanged.
The alternating plan next returns to census helper/object qualification and
broader source traversal.
