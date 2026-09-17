# Generated explicit condition dispatch

Proposal only. The accepted R2 MVC storage unit remains the integrated baseline.
This derivative adds explicit `SIGNAL`, `ERROR`, U1 `HANDLER-BIND` and
`HANDLER-CASE` (including `:NO-ERROR`) through the real front end. It claims no
inventory slot. Claude review and user acceptance are required before integration.

The target uses six owner-supplied immutable condition proxies, each a D1
simple-vector with two fields (class-membership mask and identity). They stand
for native `CONDITION`, `SIMPLE-CONDITION`, `SIMPLE-ERROR`, `TYPE-ERROR`,
`CONTROL-ERROR` and `SIMPLE-WARNING`. Nine simple class queries are tested.
This is **not the production CLOS condition layout**. Construction, condition
slots, compound types, user-defined classes, restarts, debugger entry and mapping
implicit compiler traps to conditions remain separate work.

The U1 macro expansions build their actual clusters, closures, catches and
multiple-value paths. The generated dispatcher masks the current cluster before
calling a handler; a declining handler does not consume the condition. Indexed
and single-clause handler cases use the same published nonlocal-exit machinery.
Condition identity, cluster cursors and the callable are rooted. Special bindings
restore on normal return, checked failure and nonlocal exit. A handler may return
130 discarded values under a four-word final reservation: its private result
scope uses R2 inline words and checked arena overflow, then releases that scope.
Uncaught explicit ERROR becomes checked refusal 15 after dispatch, at the
currently unimplemented debugger boundary. No collection runs in this slice.

The independent native oracle compiles the original CL forms. Its empty initial
handler chain lets SIGNAL decline normally. CCL's debugger hook records ERROR's
actual fallback after signalling, rather than catching conditions prematurely.
Literal expectations check returned values and heap effects. The target oracle
also inspects root, control and binding chains, verifies restoration and poisons
public compiled-call entries. Cold installation runs the same condition corpus
through the unchanged reviewed loader. Seven damaged proxy inputs refuse before
heap/arena writes. Ten dispatcher mutants are rejected; the visible-cluster
mutant loops on a declining handler and is rejected by a ten-second progress
deadline with the active case retained. The other nine fail explicit assertions.

The inherited MVC suite and its nineteen mutants are also replayed, including
copy/handoff observations, zero-arena checks, four regressions and long tail
chains. Condition helpers are emitted only into modules that signal. The ordinary
corpus retains its reviewed module bytes. No timing claim is made.

From the repository root:

```sh
python3 tests/wasm/stage1/b-conditions/native.py --evidence ../ccl-evidence --work /tmp/conditions-native-work --output /tmp/conditions-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/conditions-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/conditions-qualified
python3 tests/wasm/stage1/b-conditions/run.py --evidence ../ccl-evidence --native /tmp/conditions-native --qualification /tmp/conditions-qualified --output /tmp/conditions-run
python3 tests/wasm/stage1/b-conditions/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-b-conditions-r2
```

Use fresh output paths. The retained packet reuses byte-identical payloads from
reviewed prerequisite packets through explicit hash references. Its development
archive preserves original failures. R6/R6a applies and removes the proposal only
in a disposable pristine U1 copy; no shared source is changed by these commands.

R2 corrects audit 82's source-scope defect. User `CASE`, `LIST`, `POP` and `THE`
remain refused, including inside handler bodies, clauses and defaults. Their
macro-generated forms are processed only after user expressions have passed the
unprivileged walk. Fourteen refusals cover this distinction; three controls
reproduce the NIL-key wrong answer and reject both an absent form guard and a
leaked expansion privilege. The earlier packet remains retained.

`result_demand.py` is an operation-count witness, not an optimization or timing
benchmark. Its six native/target cases show that two one-valued calls under a
producer use two descriptors and three scope releases while allocating no arena
blocks. A 130-value call still allocates when used as a scalar operand, a discarded
form or a cleanup. A bounded-mode mutation fails the scalar case, so simply
turning inheritance off would be unsound. The next implementation must separate
result demand from the storage needed by internal multiple-value operations.
