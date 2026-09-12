# Reversible native observation — 12 September 2026

Codex implemented the [native observation harness](../../../tests/wasm/native-census/README.md) under the separate startup-instrumentation exception committed as 37f2b8da. The user reiterated that instrumentation must be reversible and the project must start from clean CCL. Each run extracts pristine U1 v1.13 and the pinned bootstrap into an empty disposable directory. The main checkout's compiler and upstream kernel remain unchanged. Observed images and patched sources are evidence only; they never become the implementation baseline.

## Executed scope and restoration

The retained r5 run compares a clean native build with an observed build at the same path and then removes the patch and rebuilds cleanly from the original bootstrap. Both native regression runs pass all 21,843 eligible tests; the same 75 upstream-disabled tests remain disclosed. All 164 original source FASLs are retained per build. During observation, 161 are byte-identical and three contain the explicit hooks: `l1-fasls/nx.dx64fsl`, `bin/nfcomp.dx64fsl` and `bin/dumplisp.dx64fsl`. After patch removal, all 164 rebuilt FASLs match the clean baseline byte for byte. The independent native probe also compiles identically with observation enabled and disabled.

The one hashed patch covers `compiler/nx.lisp`, `lib/nfcomp.lisp` and `lib/dumplisp.lisp` in the disposable copy. It adds conditional observer calls and preserves multiple values; it introduces no top-level initializer. Cleanup checks every archived source hash and restores 167 clean output files: 164 FASLs, the kernel, the normal image and the intermediate `x86-boot64.image`. Interrupted recovery accepts known original/patched source bytes and refuses unknown edits. Eight source-reversal controls and three output-recovery controls exercise success, failure, interruption, partial recovery and damaged-backup refusal. SIGKILL/power-loss recovery uses the retained runner's explicit `--restore` command.

Before/after comparisons use the same original bootstrap and source installation sequence. Both rebuilds declare gensym seed 100000, and installation/observation isolates its own gensym use. These are explicit compiler inputs, with no byte normalization. Six patched functions have retained native disassemblies for independent review. The three changed FASLs are identified artifacts, not a waiver for unexplained executable changes.

## What was observed

Evaluated native state is identical before and after: 279 acode slots including 12 reserved slots, their IDs/flags and dispatch readings, and 599 native vinsn template names. This is the accepted S0-LL08-b/native scope. The original raw envelope retains NOT_REVIEWED; the separate acceptance envelope records the project decision.

The build log covers 164 compilation sources, top-level reads/expansions, compile-time initializer entry/return, emitted load initializers, and function/acode observations after front-end return and before native pass 2. Nested functions can appear in more than one parent observation; occurrence counts are not unique-function counts. Call-form records retain unknown targets explicitly and do not claim complete candidate sets. The cold image executes all 35 registered startup callbacks in evaluated registration order, then reaches the listener and closes the log. Earlier runtime/stream initialization before the callback loop is outside that hook's scope.

The event writer uses a shared CCL stream with a lock around each complete record. Its fresh cold-start test crosses the Initial-process/listener boundary. Native observer controls delete pass-2 events, omit a named function, conceal an unknown indirect target, remove a reserved operator slot, corrupt operator flags and suppress completion. All six are rejected while every variant still executes the native probe with identical FASL bytes. The producer additionally rejects malformed identities, incomplete tests, incomplete restoration and a semantically corrupted evaluated snapshot even with its digest updated.

## Remaining census work

S0-LL15-b/c remain unexecuted. The logs are inputs to the complete joined graph required by [the census contract](../contracts/census.md). Outstanding work includes a reviewed seed set; conservative candidates for every reachable indirect dependency; operator-to-lowering/import/trap/store joins; semantic initializer prerequisites; and the full missing-node/edge/seed/initializer mutants. Observed callback order alone does not prove initializer prerequisite semantics. `frontend` is after `nx1-compile-lambda` returns, including its internal rewrites; it is not an unrewritten view of every front-end transformation.

The user's Terminal r2 run captured the external macOS trace successfully. The first PID-only run is preserved as failed coverage evidence. A unique executable-name filter plus PID now captures the clean image open and both coverage reads. [Reconciliation and dependency analysis](native-dependencies.md) retain four unresolved loader pathname contexts, conservative call-target work and semantic initializer joins. No internal hook substitutes for the external trace.

Claude's [sixth audit](claude-review.md) reviewed the patch, comparison setup and evidence and reproduced the run with identical FASLs and observations; the user then accepted S0-LL08-b at its stated scope; see [project acceptance](project-acceptance.md). The complete census remains open. The gate has 26 accepted records, 22 missing and one awaiting LL21-a project acceptance after correction of the misattributed authorization. B remains a dated project choice for simplicity and reviewed correctness; this work adds no ABI timing or performance-selection claim. Functional backend work requires its own authorized author and begins from pristine U1.

See [current evidence summary](../evidence/native-census-summary.json), [index](../evidence/index.json), [verification](../evidence/verification.json) and [history](../history/changes.md). Original failed runs remain retained separately.


The r7 [dependency and redefinition extension](native-dependencies.md) uses the same patch and passes its own full before/after/reversal comparison. Its new code and evidence await independent review; the accepted r5 scope is unchanged.
