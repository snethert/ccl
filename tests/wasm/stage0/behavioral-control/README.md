# Behavioral assertion control

S0-LL02-b executes a small hand-built Wasm corpus with the same assertions for
normal and mutated binaries. Requires Node with Wasm exceptions and wat2wasm on
the macOS reference host. Fresh outputs belong outside the checkout:

```sh
python3 tests/wasm/stage0/behavioral-control/run.py --output /private/tmp/ccl-behavior-run
python3 tests/wasm/stage0/behavioral-control/run.py --verify /private/tmp/ccl-behavior-run --replay-output /private/tmp/ccl-behavior-replay
```

The factory returns a descriptor containing a table entry and a separate mutable
environment. The factory call has returned before invocation; no JavaScript closure
holds the mutable values. Two returned descriptors retain independent state.
Indirect calls take self/count, read arguments from an explicit area and return
two Wasm values plus six tagged values in the caller's area. This is B-shaped
calling in a minimal fixture, not a qualification of the full CCL object layout.

Five calls test repeated capture mutation, an independent environment, a real
Wasm exceptional exit with nested cleanup, and mutation after that exit. The
ordinary assertion module checks all six values, capture contents, cleanup order
and its separate state mutation. The exceptional path publishes zero values.

Five separately emitted mutants omit the fifth value, read the initial state in
place of the mutable capture, skip cleanup, skip only exceptional cleanup, or
reverse cleanup order. Each must fail the ordinary assertions at the exact first
case. The adapter receives no mutation option. Unexpected traps, compilation
errors and timeouts fail the producer instead of counting as rejected mutants.

Original WAT, binaries, observations and failure stacks stay in `quarantine/`.
The outer envelope is CONTROL EXECUTION; inner mutants remain failed hand-built
stimuli. Fixed memory, two descriptors, integer values and one Worker bound this
proof. No collector, shared-heap threading, generated compiler or full startup
is qualified. See the [scope report](../../../../doc/WASM/stage0/behavioral-control.md).
