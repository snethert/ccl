# LL15-b/c instrument qualification

Run on the macOS x86-64 reference host, Python 3.12+:

```sh
python3 tests/wasm/native-census/qualification/run.py \
  --evidence ../ccl-evidence --output /new/qualification --work /new/disposable-work
python3 tests/wasm/native-census/qualification/run.py \
  --evidence ../ccl-evidence --verify /retained/qualification
```

The single runner uses fixed reviewed packets in `inputs.json`. It checks the
retained 167-unit startup worklist, performs fresh capture queries, privately
recompiles a real U1 call site in a disposable pristine image, runs the existing
33 capture checks and 20 native cases, then qualifies their publication with
independent omission and scope controls. It does not rerun the full native build.
The separately reviewed `query/replay_startup.py` reproduces the retained
startup analysis from native captures when that deeper replay is wanted.

`publication.py` is the unchanged checker for all publication mutants. It reads
its reference from pinned original packets, never from the candidate manifest.
`test_publication.py` edits the actual publication and regenerates its hash,
then demands a specific refusal for each edit. A matching replacement summary
cannot erase a seed, node, edge or unknown. Native implementation mutants run
through the reviewed `test_native.py` with literal value/effect oracles.

The publication distinguishes observed initial bindings and registry targets
from future unbounded changes. Native graph `implemented` and edge `complete`
labels are preserved as historical native reference claims, explicitly not
Wasm implementations or exhaustive callee bounds. All 272 body gaps and the
other five unresolved populations remain. The unchanged complete-closure
checker still rejects the worklist. The initializer sample is the actual
70-record cold boundary chain; the complete native initializer and lowering
joins and external trace are pinned separate inputs, with cross-execution and
target obligations left open. The image/compiler role artifacts are identity
manifests for the actual executed pristine image and kernel, not new baseline
copies. Original retained archives remain inputs.

The result has two HOST COMPILATION/native records. Neither record is project
accepted by this runner; Claude's independent review and user acceptance follow.
Failures keep source snapshots and logs. Temporary work is not an input to a
future run, and neither source nor FASLs are modified by private observation.

An optional `--cache /existing/capture.sqlite` reuses the query tool's disposable
index only after its input/tool fingerprint and bytes are checked. It is never
retained as qualification evidence; `--verify` builds a fresh index. The test's
damaged cache copy is also discarded after its recorded rejection.

The call partition retains every same-execution call record: 395 native IR
self/lexical/lexical-function-value sites with known local targets, 13,641
known symbol designators whose future values remain unbounded, 561 builtin
sites with unqualified lowering and 614 unresolved computed sites. A native
IR target proof does not qualify that function's target implementation.
