# S0-LL22-b: R6 comparison of the actual census registration

Run from the CCL checkout, with the retained evidence repository available:

```sh
python3 tests/wasm/stage0/r6-control/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --output /private/tmp/ccl-r6-control-fresh
python3 tests/wasm/stage0/r6-control/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --verify /private/tmp/ccl-r6-control-fresh
```

Output must be fresh and outside the checkout. Python 3.12+ and Git are required.
The runner applies/removes the unchanged accepted registration unit in an owned
pristine U1 archive. It never starts CCL or loads the retained image. Native
build/test evidence is reused, not rerun. No shared checkout source is changed.

One actual comparison passes; 44 damaged copies are rejected. See the
[scope report](../../../../doc/WASM/stage0/r6-control.md) for the four categories,
exact FASL component accounting and limits. This profile supports only the
reviewed two-entry registration patch; it is not a general FASL normalizer.

`inputs.json` pins the direct retained bytes. `cases.json` names every expected
refusal. `run.json` retains command, timestamp, source pins and original failures.
The verifier replays the actual source unit and all comparisons, matching six
deterministic files; it never rewrites the retained packet.

For permanent publication without copying the native input archives:

```sh
python3 tests/wasm/stage0/r6-control/publish.py \
  --output /private/tmp/ccl-r6-control-fresh \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --name YYYY-MM-DD-r6-control-rN
```

Publication creates a fresh packet and a root-level results envelope. It changes
only artifact and inventory locators, verifies their bytes and compares the
production gate's result. The original producer envelope is retained separately;
its `references/` hardlinks are temporary. Acceptance is a later user decision.
