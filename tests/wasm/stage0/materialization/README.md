# Template materialization

S0-LL21-c executes D2's selected materialization on a hand-built Lisp-code
template: one canonical module with an unshared, explicit-maximum memory
import yields the shared and unshared profile binaries by changing exactly
one flag byte. The materializer records template hash, offset, original
byte, limits, import and export inventories, feature requirements,
materializer version and the resulting binary hash, and refuses wrong
records, tampered bytes, non-canonical templates, unadmitted profiles and
stale identities. The same template bytes then execute under three
per-profile runtimes: the full profile's wait-based request, the
single-thread JSPI profile's suspending import and the precompiled-callback
profile's synchronous request, with identical logical outcomes. Import-limit
subtyping, growth to and beyond the maximum, and cross-profile link
rejection are recorded from the engine.

```sh
python3 tests/wasm/stage0/materialization/run.py --output /private/tmp/ccl-materialization-fresh
python3 tests/wasm/stage0/materialization/run.py --verify /private/tmp/ccl-materialization-fresh
```

Requires macOS with Node, WABT `wat2wasm` and `wasm-objdump` on PATH. The
runner disassembles every binary to classify its feature families and wait
instructions, copies the boundary fixture's binary reader into each bundle,
and takes engine admission rows from the engine matrix contract. Both
inventory variants, `shared-template` and `unshared-template`, come from one
execution. Seven mutants of the materializer, runtime check and template are
rejected by the unchanged oracle; nine production artifact-role omissions are
refused. Use a fresh output directory outside the checkout.

See [scope and results](../../../../doc/WASM/stage0/materialization.md).
