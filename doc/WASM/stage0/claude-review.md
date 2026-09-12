

## Sixth Claude audit — reversible native observation, NATIVE-CENSUS-r5 at 3ce72d35 — 12 September 2026

Reviewer: Claude Fable 5.1, in its own session on the reference host. Author: Codex, under the 12 September standing-rule exception for reversible startup instrumentation. Scope: `tests/wasm/native-census/` in full (`observation.patch`, `patch.json`, `observer.lisp`, `probe.lisp`, `inspect-native.lisp`, `run.py`, `reversible.py`, `record.py`, `analyze.py`, `trace-startup.py` and the four self-tests), `doc/WASM/stage0/native-census.md`, the S0-LL08-b/native envelope and the retained r5 evidence. Reviewer disposition only; project acceptance is separate.

### Execution evidence

Fresh run at HEAD in the reviewer's session from the pinned macos-u1-inputs into a separate disposable tree: execution PASS; both native suites 21,843 / 21,843 with 0 failed, missing or unexpected; 161 of 164 FASLs identical during observation with exactly the three patched files differing; all 164 FASLs identical after removal and clean rebuild; every archived source file restored; 167 clean outputs restored; the work tree's observation state reads inactive with all original digests matching. Against retained r5: all 164 FASL hashes identical in the baseline, observed and restored-clean builds; the evaluated snapshot and the 35-callback cold-start sequence identical; `analyze.py` yields the same counts (279 slots, 12 reserved, 599 templates, 51,342 function observations, 164 sources, 103,313 call forms, 3,647 unknown targets). Kernel and image bytes differ from r5, as they already did between the two accepted Gate 0 builds; the probe FASL differs from r5 only through its embedded source path and is identical between the reviewer's own baseline and observed compilations. `test-observer.py` against the reviewer's build: one positive, six rejected, identical probe FASL. `test-reversible.py` (8 controls), `test-clean-outputs.py` (3) and `test-record.py` against r5 (6 rejections) pass. The three original file digests in `patch.json` equal the U1 git blobs at c994217a. The r5 artifact list verifies (563 files), the producer copy of `record.py` matches the committed file, the 26 prior accepted records are unchanged apart from the disclosed path rebasing, and the gate is BLOCKED with 22 missing and one unreviewed. The main checkout has no change outside `doc/WASM`, `tests/wasm` and `CLAUDE.md`.

### Mechanism review

- **The patch is observation only.** Seven hook sites in three files, each guarded by `boundp` and a non-nil test on `ccl::*startup-census-hook*`, so an image without the observer never calls anything. The two sites that wrap an evaluated form (`%compile-time-eval`, the startup callback loop) use `multiple-value-prog1`, so values and the surrounding restart are preserved. No site touches acode, operator tables, backend state or results. The disassembly delta of the six patched functions is hook loads, `BOUNDP` calls and label renumbering.
- **Reversal is real and defended.** `ObservationUnit` refuses a Git checkout or symlinked source, checks all three original digests before touching anything, persists recovery metadata before the first mutation, applies with `git apply --check` first, verifies the observed digests, and on any exit restores from the backed-up originals and re-verifies. Recovery accepts only known original or patched bytes and refuses unexplained edits or damaged backups. The runner then restores the 167 clean outputs, rebuilds from the original bootstrap and requires 164 identical FASLs, and asserts the hook symbol is absent from the restored image.
- **The R6 comparison is fair.** Baseline and observed builds both start from the original bootstrap image, both load the same three compiled files first, and both rebuild with the same declared gensym seed; the observer isolates its own gensym use and blocks re-entry. No normalization is applied. The r2 development failure, where observer DEFVARs shifted later gensym names, is retained and was fixed by removing the initializers rather than by normalizing output.
- **The observations are checked against independent controls.** The probe requires named functions, a direct dependency, an unknown indirect target, macro expansion, a compile-time effect and multiple values, and six injected observer mutations are each rejected while the probe FASL stays byte-identical. The analyzer validates sequence numbers, a single completion, operator ID and flag consistency with the evaluated lookup, reserved-slot emptiness, and callback order equal to the evaluated registrations.

### Findings

No defect found. Six observations, none blocking:

1. **Codex amended the standing rules.** The commit adds a "clean implementation start" rule to `CLAUDE.md` attributed to a user clarification. The rule is consistent with the user's direction, but the reviewer cannot verify the attribution; the user should confirm it.
2. **Four harness files changed after r5 ran** (`test-reversible.py`, `test-observer.py`, `trace-startup.py`, `README.md`) and three were added (`record.py` and two tests). The changes strengthen controls and retention and are disclosed in the history; the six files the producer pins are byte-identical to the r5 runner copy, and the retained producer copy matches the commit.
3. **Kernel and image bytes are not reproducible across runs.** FASLs are. Any future claim about images must rest on FASL identity or a deterministic kernel build, not on image hashes.
4. **67 operator slots never appear in the build observation** (12 reserved plus 55 defined). This is census input, not a defect, but the closure work must not treat "observed during rebuild" as the reachable set; the analyzer already reports both lists.
5. **The external cold-start file trace remains unexecuted.** The runner is correct in structure, holds the client before exec and refuses to count an untraced run, but it needs administrator access that the agent session lacks. This is the one piece of the startup record only the user can produce.
6. **Startup coverage begins at the callback loop.** Runtime and stream initialization before `restore-lisp-pointers` reaches its callback list is outside the hooks, as the report states.

### Disposition

| Record | Reviewer disposition |
| --- | --- |
| S0-LL08-b, variant native (NATIVE-CENSUS-r5) | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED, at the declared scope: evaluated operator IDs, flags and reserved slots unchanged under a reversible observation patch, with two passing native suites and 164 identical FASLs after removal. Reproduced independently. |
| Build, probe, cold-start and test event logs | Reviewed as census inputs; they do not discharge S0-LL15-b or S0-LL15-c, which still need the seed set, conservative closure, joins, initializer semantics and the external trace. |

Not covered by this audit: the external file trace, the complete census graph, the census checker against a real graph, and any Wasm backend work. The implementation baseline remains pristine U1.
