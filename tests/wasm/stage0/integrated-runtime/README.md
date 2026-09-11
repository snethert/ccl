# Stage 0 integrated suspension, GC and I/O proof

This implements the hand-built **S0-LL20-a/b/c** slices on shared wasm32. It uses the existing freestanding C boundary module, a C copying collector and D5 protocol, emitted Wasm frames, and actual Node Workers. The host request endpoint only accesses stable descriptors and byte payloads. The supervisor separately inspects the heap as a test oracle.

Run from the repository root into a fresh, empty directory outside the checkout:

```sh
node tests/wasm/stage0/integrated-runtime/run.mjs --output /tmp/ccl-wasm-integrated
python3 doc/WASM/tools/gate.py --inventory doc/WASM/stage0/inventory.json --results /tmp/ccl-wasm-integrated/results.json
```

The runner requires Node, LLVM clang/wasm-ld and WABT wat2wasm/wasm-objdump. It records their versions and the host CPU/OS. The compiler selection variables are `CCL_WASM_CLANG`, `CCL_WASM_LD` and `CCL_WASM_WAT2WASM`. The reference host is macOS. LLVM clang and LLD are both pinned to 21.1.8; the default linker is Homebrew’s `opt/lld/bin/wasm-ld`, independent of inherited environment settings. Exact executable paths and SHA-256 digests are recorded. A fresh execution of both earlier boundary slices is a prerequisite of each run.

## What executes

- The bounded collector copies actual cons objects between two semispaces, preserves cycles and sharing, updates live C root records, emitted binding-frame roots and the complete VSP result region, and poisons the old space. Resumed C temporaries and Wasm locals must reload references and re-derive interior addresses.
- A worker blocks inside nested emitted/C calls. Its binding and handler state remain live. After collection, the host supplies module bytes in a stable request payload; the worker checks the digest, memory profile, imports, initialization and entry signature, installs into a slot outside the real C reservations, and calls the new function on the relocated object. Zero, one and six values are checked individually.
- Competing collectors use owner-only CAS acquisition and parity-based admission. Tests force CAS loss, a new collection during the former owner's and loser's re-entry, generation wrap, PARKED/STOPPED_GC admission, and allocation rechecking. A creator transfers its sole handoff root to a child during the initial registry scan; final rescan must include it before moving objects.
- An actual blocked foreign waiter is interrupted without completing its I/O. Interrupts and completion/cancellation race on both sides of wake publication and during rearming. Nested debugger calls use a second descriptor while the first remains outstanding; collection runs with both C frames live.
- A nonlocal exit restores the C SP and emitted root/binding/stack checkpoints while retaining its abandoned request. Retirement requires a later completed collection and a terminal host outcome before reclamation. Duplicate reclamation and stale host writes are rejected.

`schema.json` version 3 defines an aligned atomic 64-bit pair containing the request generation and wake word. Durable results are separate. The host's final wake publication uses compare/exchange conditioned on the original generation. C publishes a new generation before reusing storage. This closes a reproduced race in which a late final wake from the old request wrote the newly reused descriptor. The regression forces consumption and reuse between terminal-result publication and the old host's final wake.

The TCR also records the current active request separately from all outstanding descriptors. Nested calls save/restore that pointer; nonlocal exits restore it in the emitted adapter. Thread interrupts target the current wait, so a debugger's nested request can be interrupted while its parent's request remains outstanding. A regression reproduces and rejects notifying the parent descriptor instead.

## Schedules and rejection controls

There are 22 deterministic positive cases and 14 negative controls. The controls remove C or Wasm root reload, use fetch-add for acquisition, omit final membership rescan, set only an interrupt-pending bit, omit notification, discard a durable terminal outcome, reclaim before host acknowledgement, trap the collector, admit an unpublished child, bypass the final host wake's generation guard, interrupt the wrong nested descriptor, publish a host outcome after its final wake, or omit parking on an exceptional return. Each must produce its specific rejection evidence. Mutants and their observations remain quarantined. The two missing-notification controls and the late-outcome host mutant use an actual waiter-count witness; a failed attempt to establish that schedule cannot pass the control.

The runner also executes 1,000 seeds. A seeded scheduler chooses among runnable Workers at instrumented boundaries, in addition to selecting I/O ordering, result count and terminal outcome. Ready sets, choices, atomic-transition traces, request events and final states are retained. The seed reproduces selection rules; the retained ready sets record OS-dependent arrivals. Critical race orderings are separately forced by deterministic latches.

A concurrently polling mutator provides one measured safepoint per seed. The runner checks the predeclared 10 ms p99 / 100 ms maximum safepoint limits, the 1-second whole rendezvous limit and the 5-second schedule limit. Reported timings describe the recorded host run, not browser background scheduling or an ABI benchmark. Traps, worker exits, unexpected timeouts or expired scheduler gates fail the whole proof; the supervisor terminates every participant without clearing a failed collector's ownership marker.

## Evidence scope

The output includes source snapshots, inventory and policy hashes, compiler/link commands, objects, final modules, link metadata, per-case observations, raw seeded traces, negative-control evidence and a result envelope. No required case is skipped on the passing path. The full Stage 0 checker still returns BLOCKED because other Stage 0 IDs and acceptance reviews remain outstanding.

This is a cons-only, non-generational prototype with bounded explicit frames and two request descriptors per worker. It is not the production CCL collector, an implementation of all object layouts or Common Lisp conditions, a browser/JSPI qualification, or a D3 calling-convention selection. Compiler-generated and later-stage obligations remain required. No existing native implementation source is modified.

The ordinary emitted test entry returns `(value0, nvalues)`, using fixture NIL when there are zero values; the complete sequence occupies the caller-owned VSP region. The nonlocal-exit test restores checkpoints, parks with roots retained, then returns a separate `-1` observation marker to its supervisor. A collection runs while that Worker is idle, before retirement acquires admission. The omitted-park mutant must retain the specific idle RUNNING thread and failed collector in its failure snapshot. Ordinary return reads value0 while admitted and performs no shared-memory read after parking. JavaScript treats the returned scalar as an observation and does not dereference it. Neither selects D3 argument placement or implements the complete Lisp condition system.
