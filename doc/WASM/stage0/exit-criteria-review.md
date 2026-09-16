# Stage 0 exit-criteria review (subgate 0F) — 16 September 2026

Reviewer: Claude. Scope: the outline's Stage 0 section and the standing
requirements the acceptance policy attaches to every gate, mapped sentence by
sentence to the accepted slots and recorded decisions at wasm2 `821eac19`
(ledger PASS, 48 of 48). This is the written form of subgate 0F in
[the Stage 0 plan](plan.md): "all Stage 0 IDs, standing controls, outline
exit criteria, source/test/artifact hashes and negative controls are present;
review records actual evidence scope." It changes no record and claims no
execution; where a sentence is discharged by a decision rather than by an
execution, it says so.

Verdict: every sentence of the outline's Stage 0 section is discharged by
accepted evidence or by a recorded project decision. No new scope decision is
needed. Four census enumerations (imports, traps, direct foreign calls and
barrier-sensitive stores) are discharged by the 15 September on-demand
decision as obligations carried into Stage 1, not by executed joins; they are
listed explicitly below so that Stage 1 inherits them by name.

## Census track

| Outline requirement | Discharged by | Scope note |
| --- | --- | --- |
| Enumerate evaluated acode IDs and flags | S0-LL08-b (279 evaluated operator slots, 12 reserved, evaluated flags under R6a) | Executed, accepted. |
| Front-end elimination and rewrites | S0-LL08-b compile-effect records (18,907 entry/return pairs with function identities) and the R6a acode-identity comparison | Observed as effects and identities; there is no separate enumeration of rewrite rules. Adequate for the instrument scope; a rule-level list is not owed. |
| Native handlers, vinsns, LAP and subprimitives | S0-LL08-b (599 templates) with the reviewed emission joins (207 live handlers, 20,606 subprimitive calls to 36 targets) pinned into S0-LL15-b | Executed, accepted; joins are reviewed inputs. |
| Imports | Kernel-import census (65 imports, D6 dispositions), reviewed auxiliary | Not joined into the worklist; the graph keeps its `gap:imports` placeholder. Carried into Stage 1 under census contract v0.2. |
| Traps | D6 trap-lowering rule (decided); the 143 native check sites retained as an inventory | Vocabulary decided, join not executed. Carried into Stage 1 under v0.2. |
| Foreign calls | Eight boundary contracts (target descriptions, reviewed) | Startup surfaces named; the separate direct-foreign-call inventory is not built. Carried into Stage 1 under v0.2. |
| Barrier-sensitive stores | None executed | Pointer-store classes remain unproved by the joined census's own statement. Carried into Stage 1 under v0.2; Stage 1's precise single-thread collector (S1-LL18-a) needs no barrier, so the classification is owed before Stage 2's multi-Worker collector. |
| Instrument cross-compilation against a census stub backend for static reachability | S0-LL08-a (stub registration, 14 cases, 8 controls) with the reviewed source-wide traversal (164 native units, 103 under the Wasm target) | Executed, accepted; the worklist supersedes the static projection under v0.2. |
| Observe cold-start file opens externally and compare with the static projection | External trace and loader-context reconciliation (reviewed), pinned as an input of S0-LL15-b | Executed; every observed open classified. |
| Join operator keys to module and function keys through the instrumented record | S0-LL15-b/c: the 167-unit startup worklist with named unknowns, identity-bound queries and native witnesses | Executed, accepted at instrument scope; exhaustive closure is not claimed and not required. |
| Reversible observation precedes backend registration with its own R6 | S0-LL08-b, S0-LL22-b | Executed, accepted. |

## Architecture track

| Outline requirement | Discharged by |
| --- | --- |
| Qualify engines, EH encoding and JSPI API shape | S0-ENGINE-a: four engines, legacy encoding refused by disassembly, final try_table/exnref, JSPI present on three engines and absent on Safari; the single-thread JSPI profile is deferred from Stage 1 by decision |
| Test D1 | S0-LL04-a, S0-LL04-b, S0-LL07-a; S0-CONTRACTS-a joins the layout schema |
| Test D2 | S0-LL21-c shared and unshared |
| Test D4 | S0-LL13-c, S0-LL19-b, S0-LL13-a |
| Test D5 | S0-LL20-a, S0-LL20-b, S0-LL20-c; S0-CONTRACTS-a joins ownership; TCR schema v1 as the build target |
| Implement the selected B protocol | S0-LL05-a…d, S0-LL21-b (×3), S0-ABI-selection |
| Allocation, stores, roots, GC admission, lifecycle | S0-LL20-a, S0-LL20-b, S0-LL23-b |
| Interruptible FOREIGN I/O, mailbox | S0-LL20-c |
| EH | S0-LL19-a, S0-LL19-b |
| Lazy installation | S0-LL21-a, S0-LL13-b |
| Nested debugging | S0-LL19-a (nested debugger exit), S0-LL20-c (nested requests), S0-LL23-b (logical frames) |
| D7 phased inventories | stage0/inventory.json, 48 slots, and the D7 decision |

## Rejection tests

| Outline requirement | Discharged by |
| --- | --- |
| Omit a required module | S0-LL01-a (missing required module rejected before any initializer), S0-LL15-a (omitted required module), S0-LL02-a (omitted required test ID) |
| Alter its ABI or layout version | S0-LL21-c (wrong template hash, stale materializer version, feature and inventory mismatches), S0-LL22-a (stale and wrongly-roled artifacts), S0-LL04-a/b (target-compiled layout assertions) |
| Collide reserved memory or table ranges | S0-LL13-b (overlapping and misaligned regions, duplicate owners, wrong slot), S0-LL13-c (exact memory and table ownership), S0-LL07-a (reserved slot range) |
| Fail an initializer in the proof harness | S0-LL01-a (early, middle, late and diagnostic failures), S0-LL15-a (raise after partial write, clobbered completion) |
| A killed process or timeout is not a successful computation | S0-LL01-b (SIGKILL and timeout children fail the aggregate at the exact step) |

## Standing requirements at every gate

| Requirement | Discharged by |
| --- | --- |
| Standing controls LL03, LL22, LL23, LL24 | S0-LL03-a, S0-LL22-a, S0-LL22-b, S0-LL23-a, S0-LL24-a |
| Gate 0 baseline-identity facet of LL22 | G0-U1-a and S0-LL22-b |
| Source, test and artifact hashes | The ledger checker: 48 bindings current, 3,516 artifact references verified, 46 prior objects preserved unchanged through each addition |
| Negative controls present | Every accepted slot carries named mutants, refusals or role omissions; the tally is in the map and each report |
| Test inventories and paired-document versions checked before acceptance | The document check: projections, LL schedule, D7 inventory, local links and original-input hashes PASS at 821eac19 |
| Continuing regressions from Gate 0 | Same-host repeatability retained; the second-host test retired by the 13 September decision |

## What this review does not do

It does not reopen any acceptance, execute anything, or turn a reviewed
input into gate credit. The four carried-forward enumerations are Stage 1
obligations by the v0.2 contract's own rule that an obligation is not
removed because the instrument cannot answer it; Stage 1's plan should name
them where imports, traps, foreign calls and stores first matter (subgates
1A, 1C and 1E, and the Stage 2 collector).
