# Engine and profile matrix

S0-ENGINE-a executes the same hand-built wasm32 modules on the macOS reference
engine, Node/V8, and inside Chrome, Firefox and Safari pages served over
loopback with and without COOP/COEP. It records engine identity, feature
detection, executed multivalue, tail-call, final exception-handling,
bulk-memory and atomics semantics, the exception-encoding pin, and the full,
single-thread JSPI and precompiled-callback suspension paths. Seven named
mutants of the modules and driver are rejected by the unchanged oracle on the
reference engine, and nine production artifact-role omissions are refused.

```sh
python3 tests/wasm/stage0/engine-matrix/run.py --output /private/tmp/ccl-engine-matrix-fresh
python3 tests/wasm/stage0/engine-matrix/run.py --verify /private/tmp/ccl-engine-matrix-fresh
```

Requires macOS with Node, WABT `wat2wasm` and `wasm-objdump` on PATH, and
Google Chrome, Firefox and Safari installed under `/Applications`. Chrome and
Firefox run headless with fresh temporary profiles. Safari has no headless
mode: `open -g` loads the page in a background tab that stays open; two tabs
remain per producer or verifier run and can be closed afterwards. Use a fresh
output directory outside the checkout. The verifier re-executes every engine
and requires identical engine versions, observations and deterministic files.

`features.wat` is the canonical unshared template; the shared variant differs
in the memory flag only. `suspend.wat` carries the JSPI profile. The probes
under `probes/` are one-feature validation inputs; `legacy-eh.wat` exists so
the encoding pin can be seen refusing the prohibited encoding, and
`memory64.wat` is informational. `features.json` is the matrix contract with
the expected profile availability per engine; `oracle.py` derives every
expected value from it. Timings are never recorded.

See [scope and results](../../../../doc/WASM/stage0/engine-matrix.md).
