# Production TCR schema

The versioned TCR schema D5 owes: 47 fields in D5's nine groups with explicit
offsets, widths, alignments, classification and ownership, joined to every
replaced or deferred native TCR cell of the layout schema and to every TCR
field the accepted fixtures use. A control execution over committed
contracts; no Wasm is executed and no inventory slot is claimed.

```sh
python3 tests/wasm/stage0/tcr-schema/run.py --generate
python3 tests/wasm/stage0/tcr-schema/run.py --output /private/tmp/ccl-tcr-schema-fresh
python3 tests/wasm/stage0/tcr-schema/run.py --verify /private/tmp/ccl-tcr-schema-fresh
```

`tcr.json` is the schema source; `--generate` writes
`doc/WASM/contracts/tcr.v1.json`, and the producer refuses if the committed
file differs. Requires macOS and Python 3.

See [the schema document](../../../../doc/WASM/contracts/tcr.v1.md) and
[scope and results](../../../../doc/WASM/stage0/tcr-schema.md).
