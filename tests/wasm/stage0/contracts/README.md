# Layout schema and runtime-contract join

S0-CONTRACTS-a derives the wasm32 layout schema v1 from the pinned U1
x8632 architecture source, cross-checks it against the U1 C header, attaches
a closed source-to-target disposition ledger, and joins the frame, root,
TCR, allocation/store, C-boundary and ownership contracts to the accepted
fixtures' retained schemas, cases and link metadata by artifact hash. It is a
control execution: it runs no Wasm and confers no runtime acceptance.

```sh
python3 tests/wasm/stage0/contracts/run.py --generate
python3 tests/wasm/stage0/contracts/run.py --output /private/tmp/ccl-contracts-fresh
python3 tests/wasm/stage0/contracts/run.py --verify /private/tmp/ccl-contracts-fresh
```

`--generate` writes `doc/WASM/contracts/wasm32-layout.v1.json` and
`doc/WASM/contracts/runtime-contracts.v1.json` from the current sources,
ledger and accepted evidence; the producer regenerates both and refuses if
the committed files differ. Requires macOS, Python 3, Node (for the retained
ownership planner), Git access to the U1 blobs, and the evidence repository
named by `doc/WASM/evidence/repository.json`. `derive.py` is the reader,
`schema.py` builds and checks the schema, `join.py` builds and checks the
join, `dispositions.json` is the ledger, and `ownership.mjs` re-derives the
ownership map with the retained fixture planner.

See [the schema document](../../../../doc/WASM/contracts/wasm32-layout.v1.md)
and [scope and results](../../../../doc/WASM/stage0/contracts.md).
