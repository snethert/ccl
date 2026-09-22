# Math R2 acceptance and integration

423 original definitions execute, 394 have non-NIL witnesses: no new throughput.
Steve authorized “accept, integrate and proceed” after audit155. The compiler,
CCL source, floating service and musl source bytes are the reviewed R2 proposal.
The runtime build helper reproduces the reviewed float binary exactly. It uses
all pinned headers, including the `bits/` directory, and carries COPYRIGHT.

From the project root:

```sh
python3 tests/wasm/stage1/bootstrap-math-acceptance/run.py target --output /tmp/math-integrated-replay
python3 tests/wasm/stage1/bootstrap-math-acceptance/run.py native --work /tmp/math-integrated-native-work --output /tmp/math-integrated-native
```

Target replay explicitly builds the installed runtime, compares generated
modules and execution with the reviewed packet, and runs the forty collector
owner checks. The subprocess uses the production build helper, not an override
that exists only in its parent. Native R6/R6a uses the final installed files.
`--resume-compiled` is a development option that requires each installed compiler
and CCL source to equal the compiled run's copies before reusing them.
