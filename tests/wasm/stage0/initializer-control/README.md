# S0-LL01-a initializer failure control

An isolated Stage 0 bootstrap harness loads three hand-built Wasm modules and
runs nine required initializers. Each initializer writes observable memory state,
then either throws a real Wasm exception or records completion. Three independent
chains allow diagnostic continuation to run useful later work while dependents
of failed steps remain blocked. Ready publication requires every step to complete
and no recorded error.

```sh
python3 tests/wasm/stage0/initializer-control/run.py \
  --output /private/tmp/ccl-initializer-new
python3 tests/wasm/stage0/initializer-control/run.py \
  --verify /Users/buildsomething/Source/ccl-evidence/2026-09-13-initializer-control-r1 \
  --replay-output /private/tmp/ccl-initializer-replay-new
```

The ordinary oracle checks physical writes and call order, all step states, exact
first/all errors, return values, module preflight and ready-artifact presence.
One complete bootstrap passes. Early/middle/late failures under fail-fast and
diagnostic modes, two simultaneous scheduled failures, and a genuinely absent
module filename all fail the aggregate. Four quarantined loader mutations must
fail that same oracle. The normal loader receives no test-mutation option.

The runner pins Node and WABT executables, preserves commands and original
observations, and verifies a fresh replay. This proves the stated Stage 0 harness
behavior. It does not qualify CCL image restore, arbitrary manifests, generated
code, moving GC, threads, initializer hangs, recovery restarts or the future
Stage 1 loader. The bundle and any inner ready artifacts remain synthetic control
products in quarantine. No shared compiler/kernel source is edited.
