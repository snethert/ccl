# Floating-point detection

The D6 floating-point hypothesis says the Wasm port preserves CCL's required
floating-point conditions with explicit checks, and asks for correct
detection to be specified before its cost is measured. This fixture is that
specification made executable: hand-built checked f64 add, sub, mul, div and
sqrt that classify every result as exact, overflow, division by zero,
invalid, underflow or inexact with no engine flags, a checked
float-to-integer conversion that never traps, and the f32 default-mode
slice. Expectations for 1,882 corpus cases come from exact rational
rounding in Python, and eight mutants of the module are rejected.

```sh
python3 tests/wasm/stage0/float-detection/run.py --output /private/tmp/ccl-float-detection-fresh
python3 tests/wasm/stage0/float-detection/run.py --verify /private/tmp/ccl-float-detection-fresh
```

Requires macOS with Node, WABT `wat2wasm` and `wasm-objdump` on PATH.
`checked.wat` is the module, `ieee.py` the exact rounding and flag oracle,
`corpus.py` the deterministic corpus, `oracle.py` the comparison. This is
specification evidence, not a policy decision: which conditions the port
signals stays with the D6 floating-point choice.

See [the specification](../../../../doc/WASM/contracts/floating-point.v1.md)
and [scope and results](../../../../doc/WASM/stage0/float-detection.md).
