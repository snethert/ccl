# Reversible native startup and compiler observation

This harness starts from the pinned upstream CCL v1.13 source and bootstrap. It runs before any Wasm backend changes. It records evaluated native operator slots/flags and backend tables, top-level compiler read/expansion events, function acode observations before pass 2, compile-time initializer entry/return, emitted load initializers, and the registered image-startup callbacks as they execute.

It is an observation tool. It does not implement a backend, establish the complete bootstrap closure or turn observed calls into a conservative list of every possible callee. Missing external trace/closure evidence remains blocking for S0-LL15-b/c.

```sh
python3 tests/wasm/native-census/run.py \
  --inputs /Users/buildsomething/Source/ccl-evidence/macos-u1-inputs \
  --work /tmp/ccl-native-census-new \
  --output /absolute/path/to/new-evidence
python3 tests/wasm/native-census/analyze.py /absolute/path/to/new-evidence
```

Use separate empty work/evidence directories. Inputs are the same source, bootstrap and release-era tests as the accepted macOS x86-64 baseline; the harness downloads nothing. The runner retains commands, toolchain logs, source/patch/input hashes, native tests, all FASLs and images, snapshots and event streams. It never writes into the project compiler or kernel tree.

## Reversal and a clean starting point

`observation.patch` is one unit covering three shared source files in the disposable archive copy: `compiler/nx.lisp`, `lib/nfcomp.lisp` and `lib/dumplisp.lisp`. `patch.json` pins their exact original and observed digests. The observer owns its registration outside those source files; the patch adds no top-level initializer. Each hook checks whether the observer is present before calling it. It never changes acode or native target state.

The runner records recovery metadata and verifies all original bytes before applying the whole patch. Cleanup restores all three original files and verifies every archived source file, including after failure or a catchable interruption. It also restores the clean baseline FASLs, kernel, normal image and intermediate `x86-boot64.image`. A successful run additionally starts again from the original bootstrap, rebuilds the clean sources and requires every FASL to match the baseline. Instrumented images are retained only as explicitly named evidence and are never the port's starting point.

SIGKILL or power loss cannot execute cleanup. Recovery accepts a mixture of known original/patched files from an interrupted operation, but refuses to overwrite unexplained edits. Use the exact runner copy retained with that run:

```sh
python3 /absolute/path/to/evidence/runner/run.py \
  --work /tmp/ccl-native-census-new --restore
```

Do not use a disposable observation tree as the implementation checkout. The implementation begins from pristine U1. `test-reversible.py` exercises normal reversal, failures, interruption, partial recovery, idempotence and refusal of unknown source changes or a Git checkout. `test-clean-outputs.py` also verifies both image names, extra-FASL removal, repeat recovery and damaged-backup refusal.

## What the comparison establishes

Before/after builds use the same pinned bootstrap, installation sequence, corpus, source path, options and declared gensym seed. Observer installation dynamically isolates its own gensym use. The rebuild and probe seeds are explicit compiler inputs; no FASL normalization is performed. Changed shared artifacts remain identified for review, with disassembly of every patched function available through `inspect-native.lisp`; a filename on that list is not a blanket exemption for unexplained differences. Native regression behavior and evaluated operator identity are checked separately.

The startup log begins at the registered callback loop in `restore-lisp-pointers`, after its earlier runtime/stream setup. It crosses from the Initial process to the listener. A shared stream under an explicit record lock preserves complete JSON records across that transition. Callback return order is observed; semantic initializer prerequisites are a separate census obligation. `frontend` means after `nx1-compile-lambda` returns, which already includes its internal rewrites. It is not the unrewritten input to every front-end transformation.

The probe independently requires named functions, a direct dependency, an unknown indirect call, macro expansion, compile-time effects and multiple values. `test-observer.py` injects actual observer omissions/corruptions while requiring identical compiled probe bytes and native results. These controls qualify observation coverage at this scope, not the complete LL15 closure algorithm.

## External macOS file trace

`trace-startup.py` holds one client process before exec, attaches `fs_usage` to its PID, then lets that same PID read a coverage marker and start a clean image. Only the tracer uses `sudo`; CCL runs as the invoking user. A missing permission, coverage marker, image open, completion marker or clean trace termination cannot become a passing trace. Successful capture still needs parsing and reconciliation with the native module graph.

Run this from a Terminal with administrator access, using the clean baseline image and restored kernel from the completed run:

```sh
sudo -v
python3 tests/wasm/native-census/trace-startup.py \
  --kernel /tmp/ccl-native-census-new/ccl/dx86cl64 \
  --image /absolute/path/to/evidence/baseline/build/dx86cl64.image \
  --source /tmp/ccl-native-census-new/ccl \
  --output /absolute/path/to/new-trace-evidence
```

The current agent session lacks passwordless administrator access. Its retained trace attempt reports UNAVAILABLE and does not execute CCL without a live tracer. Internal compiler/callback observations do not substitute for this external trace.

## Retaining the evaluated operator record

After the native run, `record.py --run EVIDENCE --inventory doc/WASM/stage0/inventory.json` verifies the retained artifacts and emits S0-LL08-b/native with disposition NOT_REVIEWED. It never emits LL15-b/c or project acceptance. `test-record.py` exercises rejection of corrupt real evidence without modifying the original pack.
