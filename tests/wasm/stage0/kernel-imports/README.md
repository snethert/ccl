# Kernel-import census

The D6 kernel-import census: one record for each of the 65 U1 `defimport`
spellings with caller evidence, C or assembly definition sites, a
disposition per profile, a closure phase, a replacement and regression
obligations, plus census-shaped nodes that can replace the working graph's
`gap:imports` placeholder. A control execution over pinned U1 sources; no
Wasm is executed and no inventory slot is claimed.

```sh
python3 tests/wasm/stage0/kernel-imports/run.py --generate
python3 tests/wasm/stage0/kernel-imports/run.py --output /private/tmp/ccl-kernel-imports-fresh
python3 tests/wasm/stage0/kernel-imports/run.py --verify /private/tmp/ccl-kernel-imports-fresh
```

`--generate` writes `doc/WASM/contracts/kernel-imports.v1.json`; the
producer regenerates it and refuses if the committed file differs.
`inventory.py` joins the C and Lisp tables and scans callers and
definitions, reusing the contracts fixture's Lisp reader; `dispositions.json`
is the closed ledger. Requires macOS, Python 3 and Git access to the U1
blobs.

See [the census document](../../../../doc/WASM/contracts/kernel-imports.v1.md)
and [scope and results](../../../../doc/WASM/stage0/kernel-imports.md).
