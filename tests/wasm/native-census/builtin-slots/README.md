# Builtin slots in the working census

From the repository root:

```sh
python3 tests/wasm/native-census/builtin-slots/run.py \
  --output "$HOME/ccl-builtin-slots-NEW" --graph
```

The directory must be new and outside both repositories. The command rebuilds
the reviewed closure, revision-2 seed additions and binding-definition delta,
then integrates the builtin slots. `--evidence` relocates the sibling evidence
repository. `--base` can reuse the preceding binding-definition graph, but only
at its exact pinned hash. **BLOCKED, exit 2 is expected**; input, structure,
control or reproduction failures exit 1. No native build runs.

Five deterministic files are written:

- `facts.json.gz`: all 1,500 original call records grouped by eight operand
  slots, caller source contexts, the 23-entry native source table, target work,
  and the separate 1,562 open computed-call evidence keys.
- `delta.json.gz`: eight unresolved operator nodes, eight unresolved shared
  lowering edges and exactly 1,500 call-site replacements.
- `worklists.json.gz`: the previous named worklists preserved, plus the builtin
  population and explicit original call-gap accounting.
- `report.json`: structural result, graph counts, consolidation versus
  qualification, and the next work.
- `controls.json`: operand, table, scope and graph-corruption refusals.

`--graph` writes the full working graph as `census.json.gz`. It is reconstructed
instead of copied into another evidence packet. Source snapshots and a run
record precede analysis, including failed attempts. This command has the same
in-memory bounds as the preceding closure; no arbitrary-size claim is made.

To verify the retained result, add:

```sh
--packet ../ccl-evidence/2026-09-15-builtin-slots-r1
```

For exact historical packet verification, run from a clean extraction of
`6be15c29`: the recorded source set includes the inventory before the later LL15
policy decision. Ordinary current-tree execution remains supported, but its
source-set hash differs. The packet retains the exact executed sources.

The verifier re-executes the analysis and controls, checks source identities and
compares all five outputs. A replay without `--base` also tests reconstruction
of the preceding graph. Paths, timestamps and optional graph hashes are in the
separate `run.json`.

Known operand numbers identify operations. They do not identify original
function-cell objects or prove a Wasm implementation. The native x8664 table
maps these indices to specialized subprimitives; source text remains a native
interpretation witness. The old name placeholders remain reachable through
unresolved edges. No snapshot number is imported from a different execution.
See the [scope report](../../../../doc/WASM/stage0/builtin-slots.md).
