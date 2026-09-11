# macOS native regression baseline

The reference is macOS x86-64, using unchanged upstream CCL v1.13. This protects native behavior before future shared compiler work. The Wasm fixtures are separate engine executions.

Prepare an immutable input directory containing `source.tar` from `git archive c994217adc56b3f8a564526cee4695893ac84d86`, `tests.tar` from Clozure/ccl-tests revision `561ab1be82fefd53a61089eaad4357023e1fa961`, the official v1.13 `darwinx86.tar.gz` renamed to `bootstrap.tar.gz`, and `pins.json`. The bootstrap SHA-256 is `0eceab57e519f82bd6db011c596eb2a28e2a510abcd76e217d49a10e90f4002f`. This is the last test commit before v1.13; current-head 2026 failures remain separate diagnostics, not excluded tests within this corpus. The retained pins record the full SHA-256 of every archive and its source/test revisions. The evidence index identifies the retained input directory.

```sh
python3 tests/wasm/native-baseline/run.py \
  --inputs /absolute/path/to/inputs \
  --work /tmp/ccl-macos-native-work \
  --output /absolute/path/to/new-evidence
```

Use separate, empty work/output directories. The runner needs Xcode command-line tools, GNU m4 (`gm4`), Python 3 and the pinned archives; it downloads nothing. It uses a minimal recorded environment, builds the Darwin kernel with upstream Makefile rules, performs a clean Lisp rebuild, starts the rebuilt image and executes the unmodified pinned test corpus after LOAD returns, matching the upstream driver’s dynamic scope and default nonverbose mode. The full passed/failed test-name lists remain in the evidence. It repeats from the original bootstrap image at the same source path. Full commands, logs, evaluated eligible/disabled test inventories, results, FASLs, images, kernel and input/output hashes are retained. Source files are checked for unintended changes.

The test driver reports upstream-disabled tests explicitly and does not redefine their exclusions. A missing, unexpected or failing eligible test fails execution. Raw FASL differences remain unexplained until characterized; passing behavioral tests alone cannot establish repeatability. Native execution, same-host repeatability, second-Mac reproduction and acceptance review remain separate claims.

After a successful native run, create its verified-input gate envelope:

```sh
python3 tests/wasm/native-baseline/record.py \
  --run /absolute/path/to/new-evidence \
  --inventory doc/WASM/stage0/inventory.json
```

This verifies the retained run and artifact hashes before writing `gate-results.json`. It rejects failed/incomplete runs and never overwrites an existing gate record. “PASS” describes execution of the frozen eligible corpus; upstream-disabled tests remain explicitly disclosed in the configuration and full inventory. The envelope stays NOT_REVIEWED until an external acceptance decision exists.
