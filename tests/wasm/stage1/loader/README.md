# NSL-2 loader design of record

This proposal supersedes both P2-0 implementations: `0c3cb29f` on `wasm2`
and `7fdb2543` on `codex-loader-repair`. The user delegated the design choice
on 25 September: “use what you want to”, “dont just listen to Claude”,
“do the best design”. Audit 178 is evidence about those two implementations;
it is not acceptance of this combined proposal.

The design follows the original CCL initialization sequence, uses the existing
D2 code bundle, and leaves physical table placement to the target owner.
Functional source changes remain in disposable U1 trees pending independent
review under [the standing workflow](../../../../CLAUDE.md). Nothing here
changes the production acceptance counts or claims a complete CCL boot.

## Decisions and reasons

| Boundary | Decision | Reason |
| --- | --- | --- |
| Initialization | Shared `XFASLOAD`, with backend hooks for function names, space setup, symbol initialization, artifact writing and file compilation | Keeps kernel symbols, package construction, binding indices, documentation and the cold-load sequence in one implementation. A separate abbreviated loader would need to reconstruct these dependencies. |
| FASL representation | Dedicated opcode 72; Wasm-only version `#x80` | A distinct representation deserves a distinct opcode. The version excludes every existing native reader before it can interpret a Wasm record. |
| Compiler context | Bind the target front end around the whole file | Macro expansion, alphatizers and pass 2 must agree on the target. Per-function binding is too late for file-level expansion. |
| Nested code | Recursive code records with a private wire namespace for each function unit | Preserves captured closures and prevents independently compiled files from colliding on temporary module names. |
| Saved identity | Source locations off by default; logical fixture names | Rebuilding in another checkout must produce the same FASL, heap and code inventory. Explicit debug-source opt-in is outside that reproducibility claim. |
| Code packaging | Existing `bundle.mjs` and D2 template/materialization records | One code format, one materializer, and one generated-module ABI validator. `cross-image.mjs` coordinates heap, registry and paired-table publication. |
| Table placement | Serialize logical code IDs; supply slots through `expected.slots` at installation | Engine table positions belong to the owner. The same artifact runs with IDs 16–20 in slots 24–28 or 36–40. Existing D2 callers using serialized slots remain compatible. |

`shared.patch` records the reviewed repair's six-file delta over `1a076ca4`.
`proposal.py` verifies the base hashes, applies it in memory, changes the Wasm
version and compilation defaults, and checks the architecture generator.
It combines those six files with the 42-file accepted source identity used by
native qualification. Runtime proposals are under `runtime/`; the production
compiler and runtime in this checkout are unchanged.

The image coordinator snapshots the owner environment and slot map, validates
and compiles the entire D2 bundle, admits the relocatable heap, and resolves
symbol/code imports before installation. It publishes both tables together,
rechecks registry and static owners, installs the heap and then fills registry
records. Failures before heap installation leave memory and paired tables
unchanged. Imported modules cannot supply a start function. Initializers run
explicitly after installation, using the image's cold-load list.

## Qualification

- Two ordinary Lisp files produce five modules, including a captured closure.
  Both source files are deleted before a fresh host process cross-loads their
  FASLs. Two target cold-load functions execute; six observations match native
  in plain, collecting, relocated and relocated+collecting runs. Each collecting
  run moves live objects six times and poisons the old allocation space.
- The heap contains 241 objects, 430 relocations and 128,744 bytes. A replay
  from a Git-free checkout at another absolute path compares both FASLs,
  raw heap/static bytes, D2 templates, materialized modules and all artifact
  manifests byte for byte. It also compares observations and level-0 stops.
- 66 image checks include 65 checked refusals preserving memory and both
  tables, plus a clean installation. The keyword control assembles an actual
  `keywords.unresolved` import and recomputes D2 and outer digests. Removing
  only `KEYWORD_IMPORT` makes that control fail. The accepted D2 fixture's
  19 compatibility/publication checks also pass.
- Native R6/R6a: 21,843 tests pass; 45 FASLs are byte-identical, 119 changed
  FASLs are compared by decoded code/data and the established registration
  comparisons. All 164 baseline FASLs are restored. Generated symbol suffixes
  require prefix preservation and a file-wide bijection. All 27 existing
  loader-structure accessors/predicate are compared, including setters.
  Only the added accessors, changed constructors, named hook definitions and
  separately retained structure metadata are declared changes.
- 51 reader comparisons cover the three shared hook files under 17 existing
  target profiles. None admits FASL version `#x80`. A misplaced target guard
  is rejected. Five native-comparator mutants reject executable changes,
  interned identity changes, gensym-prefix changes, and old accessor/setter
  code changes within the structure's source span.
- The full cold compiler corpus supplies 26,048 fresh comparisons. Its source
  identity is checked against the native build and producer. Proposal source
  classification and reader baselines now use the pinned U1 archive; Git is
  unnecessary when replaying the implementation.

Independent level-0 probes compile **12 of 21 files, 452 modules** through the
whole-file front end. They enumerate target-directory files followed by the
common directory. They are neither an ordered successful build nor a target
LOAD. Nine files still stop: `l0-aprims`, `l0-array`, `l0-bignum32`,
`l0-cfm-support`, `l0-def`, `l0-hash`, `l0-io`, `l0-misc`, and `nfasload`.
The full retained messages identify the next producer work; there is no new
admission credit for these independent compiles.

## Audit 178 disposition

| ID | Result |
| --- | --- |
| O-78 | Historical constant-only target scope corrected in STATUS; this packet actually executes both cold-load functions and allocating definitions. |
| O-79 | One design of record selected above. Neither branch is merged wholesale. |
| O-80 | Source locations default off; different-root replay checks all artifact bytes. |
| O-81 | Real keyword-import refusal with recomputed digests; isolated deletion mutant killed. |
| O-82 | Existing structure accessor code stays inside the comparison; accessor and setter mutants rejected. |
| O-83 | Removed both Git dependencies. Git-free producer replay and corpus proposal classification exercised. Execution logs still retain their actual absolute command paths as provenance. |

The six shared files, generated architecture inputs and three runtime files
are a single review unit. Integration waits for review of this exact combined
identity. The previous repair's decoded native comparison is retained and
tightened; it does not authorize new functional differences without review.

## Reproduction and retained evidence

Run from this checkout on the pinned macOS host. Outputs must use canonical
paths under `/private/tmp/ccl-work/<agent>/<packet>/`.

```sh
python3 tests/wasm/stage1/loader/run.py /private/tmp/ccl-work/codex/loader-execution
python3 tests/wasm/stage1/loader/r6.py /private/tmp/ccl-work/codex/loader-native
python3 tests/wasm/stage1/loader/corpus.py /private/tmp/ccl-work/codex/loader-corpus
python3 tests/wasm/stage1/loader/readers.py /private/tmp/ccl-work/codex/loader-readers
python3 tests/wasm/stage1/loader/comparison-controls.py /private/tmp/ccl-work/codex/loader-comparison
python3 tests/wasm/stage1/loader/extra.py /private/tmp/ccl-work/codex/loader-extra /private/tmp/ccl-work/codex/loader-execution
python3 tests/wasm/stage1/loader/replay.py /private/tmp/ccl-work/codex/loader-replay /private/tmp/ccl-work/codex/loader-execution
```

`readers.py <fresh-output> --misplaced` must fail at the missing dumper
assertion. `replay.py` uses Git only to create its initial archive; the archive's
producer and corpus preparation run without a Git repository or `GIT_DIR`.

The evidence pack is `2026-09-25-loader-design-r1` in the sibling evidence
store. `packet.json` binds retained files; `compressed.json` binds the original
bytes of individually gzipped reports; `regenerable.json` identifies binaries
and intermediate WAT omitted from storage. Original development failures and
their corrections remain in `development/`. Disposable trees are deleted after
retention; existing baseline/evidence packs are referenced, not copied.

Production cross-compiled/cross-loaded/target-loaded counts remain **0/0/0**
against 167 native units; accepted originals remain **575/535** and the ledger
remains **21 accepted / 12 missing**. Fixture counts are 2/2/0. `%TOPLEVEL-FUNCTION%`
boot, target-side FASL LOAD, startup file ordering and the remaining runtime
dependencies are subsequent work. `IN-PACKAGE`/`SET-PACKAGE` is not exercised by
these fixtures. Shared FASL decoding is not newly qualified as an untrusted-input
parser; malformed-record coverage from the superseded opcode design does not
transfer to opcode 72.
