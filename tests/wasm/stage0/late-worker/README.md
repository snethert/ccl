# Late-Worker shared-state preservation

S0-LL13-b uses four actual Node Workers over one 64 KiB Wasm shared memory.
The first two mutate process data and private regions and install lazy code
before the last two exist. An independent Python oracle compares every byte
and each instance's pointers, readiness and callable table contents after all
24 transitions. Eleven invalid requests and nine implementation mutants cover
initialization and ownership; ten production artifact-role omissions reject.

```sh
python3 tests/wasm/stage0/late-worker/run.py --output /private/tmp/ccl-late-worker-fresh
python3 tests/wasm/stage0/late-worker/run.py --verify /private/tmp/ccl-late-worker-fresh
```

Requires macOS, Node/V8 with Wasm shared memory, and WABT `wat2wasm` on PATH.
The runner records the resolved executable hashes, versions and actual commands.
Use a fresh output directory outside the checkout. The verifier rebuilds and
re-executes the cases. Failed producer attempts and failed verifier replays
retain their original records and exact sources; successful replay scratch is
removed only after byte comparison.

The `.wat` files are hand-built modules. The memory layout and stack/TCR/TLS
ranges are this fixture's; no CCL object layout, C linker/TLS or generated B
execution is claimed. Tables are distinct per Worker with one agreed slot
namespace. Scheduling is ordered, not a simultaneous-start race test.

See [scope and results](../../../../doc/WASM/stage0/late-worker.md).
