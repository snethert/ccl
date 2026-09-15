# Integrated development census

Reconstruct the reviewed graph, add the accepted revision-2 seed specification
without inventing execution identities, and run the existing census checker.
This is a development feedback command. It emits no LL15 result envelope and
does not register an acceptance runner in the Stage 0 inventory.

From the repository root:

```sh
python3 tests/wasm/native-census/closure/run.py \
  --output /private/tmp/ccl-closure-NEW --graph --controls
```

The output directory must be new and outside both repositories. The evidence
store defaults to the sibling `ccl-evidence`; use `--evidence` to relocate it.
**Exit 2 is the expected BLOCKED result.** Input, reconstruction, structural or
regression failures exit 1. No native process or build runs. Source snapshots
and the initial run record are written before analysis, including on failure.

The five deterministic outputs are:

| File | Purpose |
| --- | --- |
| `report.json` | Structural result, qualification blockers and before/after counts. |
| `blockers.json.gz` | Every reachable unresolved edge and unimplemented node; membership and fan-out diagnostics. |
| `worklists.json.gz` | Original-build symbol, body, computed-call and assembly obligations with identities and evidence keys. |
| `seed-integration.json.gz` | Exact seed snapshot additions, source specification, vectors and unresolved execution bridges. |
| `composition.json` | Reconstructed historical graph identities and counts. |

`--graph` additionally writes the full exchange graph to `census.json.gz`.
`--controls` writes `controls.json`. These are integration regressions; they
cannot qualify LL15-c's independent instrumentation omissions.

To reproduce the retained packet, add:

```sh
--packet /Users/buildsomething/Source/ccl-evidence/2026-09-15-closure-r1
```

That option runs the controls, checks the packet and executed source identities,
and compares all six deterministic analysis/control outputs. It still exits 2.
Run paths, timestamps and optional graph metadata live separately in `run.json`.
The evidence packet retains the recipe and small outputs; the working graph is
regenerated from existing pinned fragments instead of archived again.

The implementation materializes the graph and indexes in memory. Its witnessed
scope is this retained graph of roughly 370,000 nodes and 1.09 million edges;
it makes no arbitrary-size or streaming-performance claim.

The original graph remains intact, including its historical conservative roots
and widening edges. New `seed-v2:` IDs belong exclusively to the seed inspection.
Only observed function literals connect those snapshot objects; every visited
body has an unresolved dependency. No numeric ID, printed name, source extent,
payload bytes or dcode literal establishes cross-execution equivalence or an
exhaustive callee bound. The separate registry witness receives zero credit
against original-build obligations. See the [scope report](../../../../doc/WASM/stage0/closure.md).
