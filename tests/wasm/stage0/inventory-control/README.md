# Required-inventory gate control — S0-LL02-a

Runs the unchanged production `doc/WASM/tools/gate.py` command against retained
version-2 control inputs. It registers and produces the actual S0-LL02-a result;
it does not execute CCL or claim a runtime/compiler result.

```sh
python3 tests/wasm/stage0/inventory-control/run.py --output NEW-DIRECTORY
python3 tests/wasm/stage0/inventory-control/run.py --verify RETAINED-PACKET
```

The fixed control inventory has three `CONTROL-*` IDs and four required variants.
Two complete inputs pass, including reordered results. Seven mutations omit the
first, middle or last ID, omit one variant, preserve the count with a wrong
variant or duplicate, or omit every result. The producer requires the exact CLI
exit status and missing-ID diagnostics. All fixture input envelopes, including
the positive controls, remain under `quarantine/` and are explicitly synthetic.
Their internal acceptance flag is test data, never project acceptance.

The outer `results.json` is actual `CONTROL EXECUTION` evidence, bound to the
current S0-LL02-a contract. Its review disposition stays `NOT_REVIEWED`.
`slot-gate.json` records a production-gate assessment restricted to that real
slot: the only remaining reason must be `unreviewed S0-LL02-a [control]`.
The production gate and binding implementation are retained unchanged with the
runner, inventory, commands and case expectations. No older evidence archive is
scanned and no earlier accepted record is rebound.
