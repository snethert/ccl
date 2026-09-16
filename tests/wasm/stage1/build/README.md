# Generated build bindings and diagnostics (1A)

`run.py` consumes the successful registration/R6 run and its independent
qualification. It checks the compiler-source join, binds the actual source,
host compiler image, host compiler modules, ABI/TCR/layout schemas, generated
WAT, Wasm modules, installed bytes, options, test revision and logs, then
installs all nine generated functions in a real table in one Node Worker.
Thirty-seven preflight/slot controls reject stale identities, mixed binaries,
missing roles and corrupt installed slots. The native qualifier additionally
rejects an unexplained FASL and changed executable components.

The fatal reporter is the unchanged, reviewed Stage 0 implementation. Its
new map decoder accepts only the initial emitter's complete binary shape.
Out-of-bounds argument reads, out-of-bounds result writes and an entry arity
invariant failure trap in **compiler-generated** code. The engine's function
index and binary offset determine the fault; an independent WABT disassembly
checks the reported instruction. Last-observed context deliberately names a
different function. The report carries the manifest and installed-binary
hashes, logical code ID, B entry kind, actual structural signature and actual
table slot. Twenty-five failures retain the first and three diagnostics,
count twenty-two drops and stay within 8 KiB. Hidden/unreadable top frames
remain unattributed. Eight single-site reporter mutants must fail the same
oracles. A failed early control whose last error duplicated its first is
retained; the final flood uses a different operation so overwriting the first
failure is observable.

Scope: a V8 stack parser, one Worker, nine nonallocating leaf functions.
The bound image is the **native compiler image**, not a Wasm bootstrap heap.
The loader and emitter subset are proposed production components under
`tests/wasm/stage1`, pending Claude review before integration. Ordinary Lisp
arity conditions remain S1-LL05 work; these diagnostic tests do not discharge
that condition obligation or any general B-ABI test.

```sh
python3 tests/wasm/stage1/build/run.py \
  --native "$NATIVE_RUN" --qualification "$QUALIFICATION" --output "$NEW_PACKET"
python3 tests/wasm/stage1/build/verify.py --packet "$PACKET" --evidence "$EVIDENCE"
```

The verifier replays the native-image qualification, generated binaries,
binding refusals, actual engine faults and all diagnostic mutants. For a
fresh full R6 build, run the registration recipe first. All proposed shared
edits remain in the packet's reversible unit; no main-tree compiler or kernel
source is changed.
