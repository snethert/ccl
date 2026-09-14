# KERNEL-PATH resource identity

Capture the original U1 source boundary and a separately named replacement
through the Wasm census front end. Execute the replacement against a private
native reference for its loader service. No upstream definition is installed,
source edited, FASL emitted or Wasm runtime implementation claimed.

```sh
python3 tests/wasm/native-census/kernel-resource/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-resource-work-fresh \
  --output /private/tmp/ccl-resource-output-fresh
python3 tests/wasm/native-census/kernel-resource/run.py \
  --verify /private/tmp/ccl-resource-output-fresh
```

Requires the macOS x86-64 reference host, Python 3.12 or later and the retained
native input pins. Both directories must be fresh and outside the evidence
store. The runner makes a disposable U1 archive copy. Two normal sessions must
produce identical captures; eight source mutants run in separate processes.
The verifier rechecks the retained captures and derived records without another
native execution. In the published packet, pass its `execution` subdirectory
to `--verify`.

The fourteen reference cases cover readiness, input validation, installation
once, input/output ownership, recovery after refusal and opaque Unicode names.
The service's private special variables stand in for future process-owned
loader state. This is a single-threaded reference; Wasm string allocation,
roots, publication and target conditions remain obligations.

See [scope and results](../../../../doc/WASM/stage0/kernel-resource.md).
