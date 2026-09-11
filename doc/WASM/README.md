# CCL WebAssembly port

The implementation baseline is upstream CCL v1.13 at `c994217adc56b3f8a564526cee4695893ac84d86`. The earlier design and execution reports used `4ca4df402e319789401cd33e680702e51ec601fc`; those results remain historical and do not qualify this checkout.

## Current documents

- [Port outline v0.17](outline.md): requirements, architecture and delivery stages.
- [Acceptance policy v1.7](acceptance.md): R6 comparison boundaries, R7 evidence and LL01–LL24 obligations.
- [Stage 0 decisions v1.8](decisions.md): D1–D7, phased experiments and initial contract references.
- [Stage 0 work plan](stage0/plan.md): subgates, dependencies, deliverables and execution commands.
- [Workflow](workflow.md): independent census and architecture tracks.
- [Current status](STATUS.md) and [dated change history](history/changes.md).

Markdown is the editable document source. The three versioned DOCX files are generated reading copies. `stage0/obligations.json` and the stage lists are generated from the acceptance register's LL metadata; `stage0/inventory.json` defines the individual tests. These complementary sources are checked together. Seven reviewed native/runtime/frame records are now accepted within their stated scopes; the remaining Stage 0 obligations are open.

## Reproduce the document package and initial probes

Run from the repository root. Document tools use Python 3's standard library. The initial execution probes additionally require Node.js and WABT `wat2wasm`; their exact versions are recorded when run.

```sh
python3 doc/WASM/tools/manage.py generate
python3 doc/WASM/tools/manage.py check
python3 doc/WASM/tools/test-controls.py
python3 doc/WASM/tools/test-bindings.py
python3 doc/WASM/tools/test-acceptance.py
node doc/WASM/tools/run-probes.mjs --output /tmp/ccl-wasm-probes
python3 doc/WASM/tools/gate.py --inventory doc/WASM/stage0/inventory.json --results /tmp/ccl-wasm-probes/results.json
```

The last command must report BLOCKED and exit 2 for the initial probe results: these probes intentionally cover only part of Stage 0. They have distinct `PROBE-*` IDs and cannot substitute for required `S0-*` acceptance tests. A failing probe exits nonzero. Full acceptance additionally requires artifact verification and a recorded review disposition; the gate tool is a completeness/provenance check, not a source of independent acceptance.

The [C/runtime boundary fixture](../../tests/wasm/stage0/runtime-boundary/README.md) additionally uses LLVM clang and wasm-ld to exercise S0-LL13-c and S0-LL19-b. It runs on macOS with Node/V8; macOS is the project reference host. Run it into a fresh, empty output directory:

```sh
node tests/wasm/stage0/runtime-boundary/run.mjs --output /tmp/ccl-wasm-runtime-boundary
python3 doc/WASM/tools/gate.py --inventory doc/WASM/stage0/inventory.json --results /tmp/ccl-wasm-runtime-boundary/results.json
```

Two passing boundary results still leave the full inventory BLOCKED. Native Gate 0 is a separate regression baseline before shared compiler changes; the same macOS reference host runs the native baseline and these Wasm fixtures.

The [integrated runtime fixture](../../tests/wasm/stage0/integrated-runtime/README.md) extends that work with real object movement, GC admission/lifecycle schedules, code installation and interruptible I/O:

```sh
node tests/wasm/stage0/integrated-runtime/run.mjs --output /tmp/ccl-wasm-integrated
python3 doc/WASM/tools/gate.py --inventory doc/WASM/stage0/inventory.json --results /tmp/ccl-wasm-integrated/results.json
```

Each integrated run first executes the earlier C-boundary prerequisites. [Current evidence and review](stage0/integrated-runtime.md) distinguish the passing hand-built slices from remaining Stage 0 work.

The original DOCX files and PNG are retained byte-for-byte in [history/2026-09-11-inputs](history/2026-09-11-inputs), with hashes in [history/inputs.json](history/inputs.json). The PNG is superseded by the current workflow. Historical evidence availability is recorded separately in [evidence/index.json](evidence/index.json); missing archives have no invented locator or digest.

Current fixture packs and original integrated-runtime failure packs stay in-tree. The larger ABI development failures remain fully retained in the separate evidence repository, with archive hashes and locators in the index. Superseded packs are retained in an external local evidence store with full hashes and locators in the index; a locator is not a claim of remote backup. Version 2 records match the current per-test contract, its prerequisites and the inventory version under the [evidence-binding contract](contracts/evidence-binding.md). Unrelated inventory additions do not invalidate earlier results. Original whole-inventory hashes and execution records remain unchanged; legacy envelopes require a verified, separate format upgrade.

The native reference and reproduction procedure are in [baseline.json](stage0/baseline.json) and the [macOS runner](../../tests/wasm/native-baseline/README.md). [Claude’s external audit](stage0/claude-review.md) records findings and fixes; post-audit verification does not imply acceptance.

The next D3 prerequisite now has a [logical debugger-frame fixture](../../tests/wasm/stage0/debug-frames/README.md), with [execution scope and remaining work](stage0/debug-frames.md). Claude independently reproduced and reviewed r3 without finding a defect. Claude also reviewed the v2 evidence tooling at 52639e4e. The user authorized the separate [scoped acceptance decision](stage0/project-acceptance.md).

The [product-risk plan](stage0/product-risk-plan.md) couples startup, scale and module granularity with C/C4/B measurements. H(G) is optional future work and blocks no scheduled stage. The [separate evidence repository](evidence/repository.json) preserves original runs and supplies a portable hash catalog.

The [C/C4/B correctness corpus](../../tests/wasm/stage0/dynamic-call/README.md) now executes arguments, multiple values, tail transfer, lazy installation and restoration through one parameterized fixture. Its new evidence awaits independent review. Reproduce it with:

```sh
node tests/wasm/stage0/dynamic-call/run.mjs --output /tmp/ccl-wasm-dynamic-call
```

The [dynamic-call report](stage0/dynamic-call.md) identifies bounds, original failures, retained artifacts and the next D3 work. Passing this corpus does not select an ABI.
