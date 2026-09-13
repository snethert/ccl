# Native boot-process execution witness

The boot-image subprocess now has its own observation record. The earlier rich compiler capture never loaded its observer in that process, so it could not establish the execution of the cold initializer queue or L1 installations. The new [reversible fixture](../../../tests/wasm/native-census/boot-observation/README.md) starts recording immediately before U1 drains `*xload-cold-load-functions*` and stops at the explicit normal-top-level handoff. It runs in a disposable pristine U1 archive on macOS x86-64.

Claude reviewed this as acceptable at its stated execution scope, with no defect, in the [sixteenth audit](claude-review.md). The source-identity limitation below must remain explicit during integration. It supplies observed execution identities; the complete LL15-b/c exchange graph still needs assembly and qualification. Stage 0 remains 28 accepted, 20 missing and zero unreviewed required records. No acceptance envelope changes.

## Executed scope

| Observation | Count |
| --- | ---: |
| Events | 52,441 |
| Cold initializer calls, each with a return | 133 |
| Completed file loads | 121 |
| Completed loader initializer calls and reader frames | 8,326 each |
| Additional load / reader / initializer frames active at handoff | 1 each |
| Distinct loaded files / witnessed initializer opcode bytes | 122 / 8,327 |
| Function-cell installations / removal intents | 9,335 / 9,289 |
| Binding symbols with initial and final checkpoints | 9,094 |
| Retained object descriptions | 26,811 |

The recorder retains actual function objects, reader functions, dispatch tables and old/new function-cell values. It never retains the dynamic-extent FASL state. Each reader event carries the filename and actual opcode offset; every recorded byte agrees with the corresponding retained FASL and U1's `$fasl-lfuncall` encoding. Names and source notes are descriptions read after image save/restore, not historical mutable metadata or cross-process identity witnesses.

All 133 cold initializers are anonymous: their retained names are `NIL`, with no source file or source position. They have distinct object identities within the boot process, but this packet cannot map them to source forms or modules. Until an xload-side witness records their queue insertion sites and supplies a justified positional join, census integration must retain them as order-only nodes with unresolved source dependencies.

A separate retained copy of the original cold queue checks execution order and coverage. A first-touch binding checkpoint supplies each symbol's initial value. Replaying the installation/removal events must agree with that initial state and with bindings independently read from the saved image. The first installation remains checkable even if startup later overwrites it.

Removal is recorded immediately before U1's original primitive clear, as an intent. No successful observation is issued for a failed boot. The outer startup load, its FASL reader and its final initializer transfer into the top level without returning; the record preserves those three active frames at handoff instead of inventing completion.

## Reversibility and verification

Only `level-0/l0-def.lisp`, `level-0/nfasload.lisp` and `level-1/level-1.lisp` are patched, together, in the disposable archive. The patch adds inline recording at the existing stores, calls and handoff. It adds no top-level definitions or initializer forms. The owner thread writes a cons list through primitive accessors; serialization happens after startup. Any writer with a different TCR identity sets a sticky refusal flag. No new special binding is needed before U1 assigns binding indices.

The clean and observed native suites each pass all 21,843 eligible tests, with the same 75 upstream-disabled cases disclosed. All 161 unmodified FASLs are byte-identical during observation. The three intentional differences are retained for review. Evaluated native snapshots agree, including operator IDs/flags, target state and template names. Removing the unit and rebuilding from the original bootstrap restores all 164 FASLs byte-for-byte. The kernel is the previously retained unchanged U1 kernel.

Twenty-five stream/file controls reject omissions, substitutions and insertions. Two recovery cases pass and five unit guards reject partial patches, changed inputs, checkout use or damaged restoration state. Saved-image controls additionally exercise the actual `%fhave` owner's refusal branch, an active recorder at export, and an omitted cold return with repaired sequence/counts. A fresh unaltered export must be byte-identical to the retained stream. The [summary](../evidence/boot-observation-summary.json) identifies the finalized packet and verification records.

The first development boot trapped because the recorder incorrectly treated `%current-tcr`'s encoded identity as a foreign pointer. A later run exposed generated-name drift caused by extra top-level handoff forms; keeping one initializer at the existing site removed every unexplained FASL difference. An omission control then exposed the missing first-binding checkpoint. Export/parser and verification-driver failures are also retained, with their exact source variants and logs. The first failed boot's original binary was overwritten by clean-output restoration before failure-binary retention was added; its original log, command record, patch and inputs remain. No reconstructed binary or successful rerun is presented as that original evidence.

## Remaining census work

These are native boot-process identities. The next exchange fragment must preserve that namespace and join it to other captures only with explicit witnesses. No name-only merge, Wasm implementation disposition or full static dependency bound is supplied by this packet. The registered-target source traversal, reviewed seeds and conservative dynamic-call bounds, remaining lowering/import/store classifications, and the complete closure checks remain open.

Object retention makes this unsuitable for allocation, GC cost or startup timing claims. It observes function-cell transitions through the instrumented U1 paths, not every possible store to every kind of binding. The observed source and images are evidence only. Implementation continues to start from clean U1 source and bootstrap.
