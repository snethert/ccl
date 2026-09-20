# S1-LL16-a: joined numeric qualification

This unit qualifies the adopted Stage 1 numeric subset through the integrated
compiler and runtime. It changes no compiler or runtime source. The compiler
and rebuilt numeric binaries must equal their reviewed, integrated packets;
reviewed native R6/R6a is reused by those identities.

The generated corpus combines all 4,553 independent integer cases at three
native safety/speed policies with the accepted 4,379 floating cases and twelve
checking-cost cases. The Python integer oracle is regenerated, native CCL
compiles and executes each expectation, and generated code runs below and above
2 GiB with ordinary and forced-moving allocation, eagerly and cold-installed.
The same 59,083 rational-oracle cases exercise the primitive's original entry.
The user-selected native bignum coercion rule and the approved D6 exact-tiny
difference remain explicit. See [scope.json](scope.json).

Primitive and detector call graphs are decoded from the actual binaries and
must have no cycles or indirect transfers. Generated integer leaves also run
with both function tables cleared, including slow bignum calls. This rules out
fallback through generated Lisp without using a fuel guard as a semantic fix.
Four altered numeric-operation instructions must fail native-derived cases;
publication omissions and malformed dispatch graphs must be rejected separately.

Checking cost is measured on six generated 64-operation loops, with paired
checked/unchecked trials in seeded random order: one second warmup per mode,
thirty 250 ms samples per mode/workload, raw durations and counts, and paired
bootstrap intervals. Warm eager calls include roots, service staging, allocation,
and return. The harness resets the heap between invocations and asserts no
collection. Cold installation is tested for correctness separately. The results
are descriptive for this host and engine, with no application-speed or ABI claim.

```sh
python3 tests/wasm/stage1/numeric-qualification/run.py \
  --evidence ../ccl-evidence --output /tmp/ll16-new
python3 tests/wasm/stage1/numeric-qualification/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-numeric-qualification-r1 \
  --output /tmp/ll16-replay
```

The verifier rebuilds the compiler in disposable pristine U1, reruns native and
Wasm execution and every new control, and takes fresh timing samples. It compares
semantic artifacts byte-for-byte. Benchmark durations are retained as fresh
measurements, not treated as deterministic outputs. No historical `/tmp` path
is an execution input.
