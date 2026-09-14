# Lexical callback bounds

Observe the untouched compiler IR for source-rebuilt DECLAIM and APPLY
expanders. Join their computed MAPCAR calls to immutable lexical bindings and
exact local function prototypes. Check eight genuine target-front-end probes,
21 damaged-input controls and repeatability in two native sessions.

```sh
python3 tests/wasm/native-census/lexical-callbacks/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-lexical-work-fresh \
  --output /private/tmp/ccl-lexical-output-fresh
python3 tests/wasm/native-census/lexical-callbacks/run.py \
  --verify /private/tmp/ccl-lexical-output-fresh
```

Use fresh directories outside the implementation checkout. Requires the macOS
x86-64 reference host, Python 3.12 or later, and the pinned native inputs already
in the evidence repository. No native rebuild or generated Wasm execution.

See [scope and results](../../../../doc/WASM/stage0/lexical-callbacks.md).
