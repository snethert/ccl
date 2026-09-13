# Required-child failure control

S0-LL01-b exercises the unchanged `run()` and `command()` functions in
`tests/wasm/native-baseline/run.py`. It requires the macOS x86-64 reference host
and Python 3.9 or newer. It does not build or execute CCL.

From the repository root, choose fresh directories outside the checkout:

```sh
python3 tests/wasm/stage0/child-command-control/run.py --output /private/tmp/ccl-child-control
python3 tests/wasm/stage0/child-command-control/run.py --verify /private/tmp/ccl-child-control --replay-output /private/tmp/ccl-child-replay
```

The adapter loads the actual producer with `runpy`, replacing only its command
invocation binding. Every invocation forwards through the original `command()`;
the subprocess implementation, completion checks, exception handling, report
construction and aggregate return status all remain original. Both original and
effective command lines, environment, markers and timeouts are retained.

The replacement commands create explicitly synthetic source/build/test products.
One complete workflow reaches PASS. At kernel build, Lisp rebuild and the final
test command, children really exit 23, kill themselves with SIGKILL, or block
until the production command's one-second timeout kills and reaps them. Each
first writes its expected outputs and completion marker, where applicable. A
tenth negative case exits zero but omits the required rebuild marker. The oracle
requires the exact command prefix, terminal outcome, identified failing step,
aggregate failure and absence of later commands.

`quarantine.zip` retains all original sandbox files, including failed-command
logs, partial products and unchanged inner reports. Those reports have the
production writer's native label, but their input revisions explicitly say
`SYNTHETIC-NOT-U1` and `SYNTHETIC-NOT-UPSTREAM`. They must never be offered as
native execution evidence. Only the outer S0-LL01-b envelope is actual CONTROL
EXECUTION. No compiler, native baseline or Wasm result is gained.

Verification reads the retained archive and reruns all eleven cases in the fresh
replay directory; it preserves new original logs there and compares semantic
observations. It does not modify the original packet. Raw timestamps, elapsed
times and absolute paths are expected to differ and are not claimed identical.

This covers this production aggregate's required-child outcome handling. It does
not establish descendant-process-tree cleanup, process-group cancellation,
initializer propagation (S0-LL01-a), or every other project's runner.
See the [scope report](../../../../doc/WASM/stage0/child-command-control.md).
