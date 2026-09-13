# Bootstrap design review — 13 September 2026

Status: Codex's assessment and proposed implementation priorities, recorded at the user's request after discussing Claude's [attempt-1 survey](../history/attempt1-reference.md). The survey is historical reference, not qualified U1 evidence. This review changes no accepted result, Stage 0 gate, compiler-author authorization or frozen architecture decision.

## Decisions retained and assumptions to test

The survey gives no demonstrated reason to reverse the [current decisions](../decisions.md): the x8632-derived layout, B, the C-kernel/emitted-subprimitive split, explicit exception handling and the GC admission protocol remain in force. The reviewed fixtures establish mechanisms at their stated bounds. Compiler integration and complete bootstrap remain unproved. B remains an engineering choice on simplicity grounds, with no benchmark-selection claim.

Four assumptions deserve earlier implementation evidence:

- **Bootstrap phasing.** The reported loader/error-system cycle calls for explicit phase prerequisites and activation boundaries. Observing native initializer order does not establish that a Wasm bootstrap can satisfy the same dependencies.
- **Packaging.** Thousands of single-function modules and a subsequent merge pipeline are reasons to try coherent bootstrap bundles. They do not establish an optimal module size or a performance advantage for any ABI.
- **Heap identity.** Separate logical code IDs do not by themselves preserve shared constants, classes, symbols and closure environments through cross-dumping and loading.
- **Reuse and effort.** The survey's reported 79 shared-file modifications warn of integration cost. Its different baseline, architecture and compiler workarounds make that count unsuitable as a forecast for U1. Native-source reuse and the project's effort estimate remain assumptions to test through generated code.

## Bootstrap work to make concrete

The census and first generated bootstrap should identify the services available in each phase, the dependencies installed before entering it, and the assertion that permits the next phase. A candidate progression is:

1. Establish the required memory/root and entry mappings, canonical objects and the minimum loader and fatal-diagnostic dependencies. An initializer must not depend on a service scheduled only for a later phase.
2. Install the required Lisp definitions while the bootstrap failure path remains usable. Identify the prerequisites and completion boundary for activating the ordinary error services; preserve the relevant binding versions across that transition.
3. Enter the supported Lisp workload. Enable lazy installation only where the installer's complete dependency set is already available, including its failure path.

U1 source and the qualified census determine the actual phase boundaries and eager dependency set. The archived `/full` renaming and `fset` activation workaround is not selected here. Early failure can remain a structured fatal diagnostic under D6 until the supported condition path exists. This elaborates LL01/LL15/LL19; it does not require a full condition system before the first bootstrap instruction.

For the first generated bootstrap, **a small number of coherent, eagerly installed bundles is the proposed starting configuration**. Exact partitioning and production granularity remain Stage 1 decisions. Keep logical code IDs, function identity and entry mappings independent of packaging, and preserve old function objects when code is redefined. Record the chosen configuration and assess startup with useful generated code. This proposal adds no timing sweep or comparative ABI prerequisite.

## Progression from the first generated slice

The existing two-function B slice remains a useful first executable milestone. Extend it incrementally through closure capture, dynamic binding and multiple values, including legal GC and exceptional restoration, before relying on the backend for a large bootstrap. Then exercise the actual front end, B emission, cross-dump, fresh-process loading, initializer transition and a successful Lisp call together. Native U1 supplies the semantic comparison; builder caches and observation images are absent from the implementation baseline.

That image proof should include two functions referring to the same mutable constant, distinct closure environments with intentionally shared captured cells, package-qualified symbols and binding aliases, and canonical NIL and keywords. Verify both identity and observable mutation after loading and legal GC. Include shared class objects when they occur in the selected bootstrap closure; this does not pull all CLOS breadth into the first slice. Reconcile the host/target hash representation before package lookup. These are concrete applications of LL06/LL09–LL12/LL14/LL16–LL19, not new inventory slots or claims of execution.

Supporting those semantics early tests whether shared-source workarounds for missing closures, dynamic binding or multiple values can be avoided. Record the actual required shared edits and their native regression cost as they become known. Execution follows the clean U1 baseline and author scope in [CLAUDE.md](../../../CLAUDE.md); this plan does not authorize functional compiler work by an otherwise restricted author.

## Historical prescriptions and current contracts

The survey includes remedies from the failed implementation. Their applicability must be established separately:

- **Memory spacing:** derive and check every reserved range and initialization owner under D4/D5 and LL13. A fixed 1 MB gap is not a current allocation or collision-prevention rule.
- **Class references:** preserve the declared object graph and identity under LL12/LL14. Name lookup is suitable only where explicit reconstruction semantics justify it; it is not a general replacement for shared class or instance references.
- **Rebuilds:** reject stale or conflicting code/entry mappings under LL11/LL21. The archive's full-rebuild workaround does not establish a blanket prohibition on incremental compilation or supported redefinition in this design.

The next architectural confidence comes from the generated bootstrap path above. Existing hand-built evidence continues to qualify only its recorded scope.
