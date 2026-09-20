# S1-LL21-b: production module granularity

Select **one generated Lisp function per Wasm module**, with public and internal
B entries together. A closure's environment stays in the heap; creating another
closure does not create another code module. Retain old modules and slots across
redefinition. Do not recycle them while old function objects remain live.

This is the simple existing packaging, now measured and bound to a complete
code-set map. Benchmark policy v3 permits an engineering choice without a merger
ranking. No merged candidate, speed advantage, statistically optimal granularity,
or complete bootstrap workload is claimed. The measured corpus covers the
current production emitter's required/optional/rest/keyword entries, five inner
closure modules, mutable environments, multiple values and three redefinitions.
LL15 still owes the final bootstrap inventory; the packaging rule applies to its
functions, while these small-set costs are not extrapolated to boot latency.

`bundle.mjs` is an unintegrated owner/build proposal. Each logical code ID maps
to a generation, module, two export roles and structural signatures, slots,
body extents, ABI/layout versions and the accepted D2 identities. The expected
inventory is a trusted owner input. IDs and slots need not be equal (a reversed
slot permutation is admitted); the fixture's execution uses its inherited equal
assignment. Entire-set validation precedes compilation; instantiation precedes
publication. Occupied/reserved slots, omissions and wrong roles refuse. Failed
publication rolls back newly written entries. No merge fallback exists, so a
failed set cannot silently omit a function. The production lazy loader is unchanged.

A fresh disposable U1 compilation of the accepted compiler reproduces the 16
reviewed metadata modules exactly. Three real compilations change the optional
default of `plain`. Native CCL rebinds a fresh symbol while retaining the old
function and supplies each new answer. The target owner publishes each new code
version, changes its selected binding, dispatches through the registry's slot,
and calls the old function again. Snapshots retain the original function,
distinct closures with mutable captures and all three newer functions. Workers
created afterwards at 2 MiB and 2 GiB install those versions and repeat the
answers. This uses the reviewed snapshot fixture, not LL14 or a production
symbol installer; LL11-a separately qualifies named-symbol transactions.

## Measurements

Thirty fresh Node processes each compile the full set once. Cold compile,
instantiate and table publication are timed separately; this avoids cross-trial
engine caches. Warm instantiate and complete validated-install measurements use
30 trials of at least 250 ms after a 1 s warmup, with explicit GC between trials
and ordinary GC included inside each sample. Full installation includes mapping
validation, digesting, D2 re-derivation, engine compile/cache lookup,
instantiation and publication. Input file reads are outside the timed intervals;
slot clearing is included. Timings are descriptive, not v3 comparative selection.
The host is recorded, without an exclusive-host claim or browser extrapolation.

Retained-code growth is measured with strong module references at generations
1–4, using the pinned V8's `--print-wasm-offheap-memory-size` diagnostics at
shutdown. NativeModule totals are separate from shared WasmEngine overhead.
Default/lazy and eager Liftoff-only diagnostic runs are separate populations.
This is engine-reported module off-heap storage, not an isolated machine-code
byte count or a GC reclamation claim. Encoded bytes, gzip sizes and whole-process
RSS/heap counters are also retained and labelled separately. No references are
dropped to manufacture a flat retention curve.

The retained run has 19 modules / 197,431 bytes. Median full-set cold compilation
is about 1.93 ms; warm instantiation 0.18 ms; complete validated installation
37.1 ms. Digest/record checking is construction work and dominates the latter;
it is not a per-call cost. Default NativeModule storage grows from 237,657 to
284,019 bytes; eager Liftoff storage from 458,778 to 549,180 bytes. These costs
make the tradeoff explicit: independent installation and simple identity at the
price of repeated per-module helper bodies and validation. Revisit packaging if
the completed bootstrap measurements demonstrate that cost is unacceptable.

## Replay

```sh
python3 tests/wasm/stage1/granularity/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-granularity-r1 \
  --output /tmp/granularity-review
```

Replay recompiles and re-executes semantics, the eight implementation faults,
19 refusals and seven independent publication controls byte-for-byte. It checks
retained raw measurement arithmetic and policy minima; times are not required
to reproduce. To collect fresh timings, run `run.py --evidence ... --output ...`
without `--no-timing`. Native R6/R6a is reused from accepted LL21-a by exact
compiler hash; no compiler, kernel or runtime source changes here.
