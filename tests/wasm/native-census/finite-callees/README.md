# Reproduce the finite-callee chain

This is a bounded replay of the four existing resolver passes. It adds no new
resolver and supplies no LL15 acceptance. The original 1,562-site population
remains partitioned into finite expressions and explicit unknowns. A finite
symbol expression still points at an unresolved function-cell value.

From the repository root, choose a fresh work directory outside the repositories:

```sh
census_work=$(mktemp -d)
python3 tests/wasm/native-census/builtin-slots/run.py \
  --output "$census_work/builtin" --graph
# BLOCKED / exit 2 is the expected builtin result. Do not interpret other exits
# as success. Continue only after the report says structure PASS.
python3 tests/wasm/native-census/finite-callees/reproduce.py \
  --base "$census_work/builtin/census.json.gz" \
  --output "$census_work/chain"
```

`--evidence` relocates the evidence repository. `--source-root` selects a clean
source extraction, such as the one retained in the packet. `--stage` can run a
single named stage; existing stage output is refused, and a different analysis
source set from an earlier recorded stage is refused before execution. Each
stage retains its command, input hashes, source hashes, resolver sources, driver,
log and outcome. The original runners' refusal controls execute unchanged.

The stages are finite expressions, lexical argument/capture flow, lookup native
probes and lookup analysis, constructor input extraction, constructor native
probes and constructor analysis. The constructor input step regenerates only
CONSTANTLY's required body correspondence from the retained original and
correlated streams. It does not consume the unpublished broad body-join chain.
Native probes run in disposable U1 copies; no source patch is applied or FASL
published. Do not use those copies as the implementation baseline.

The pinned replay uses the analysis code from `e0c73b10`, unchanged from
`6be15c29` for these resolvers. Its partitions are:

| Pass | New finite expressions | Still unresolved |
| --- | ---: | ---: |
| Finite | 98 | 1,464 |
| Lexical | 19 | 1,445 |
| Lookup | 2 | 1,443 |
| Constructor | 5 | 1,438 |

The earlier development history reported 95 then 22 because the first pass's
sources changed between runs. That history is retained, not rewritten. The
current replay proves the 124 total from one committed resolver version.

`verify.py` and `lexical_run.py verify` separately replay their selected IR,
partitions, graph edits and controls. Later passes run their native literal
oracles and graph controls during production. The final proof set, preserved
bounds, remaining-site list and constructor delta equal the earlier terminal
values. The full graph intentionally differs: this replay contains the four
callee passes without interleaving the old, unpublished body-analysis graph.

See the [scope and retained evidence](../../../../doc/WASM/stage0/finite-callees.md).
