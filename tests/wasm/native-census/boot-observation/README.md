# Early boot observation

This unit records the native boot-image process before it can load an ordinary observer: the retained cold initializer queue, loader invocations, the actual FASL reader and callable identities, and function-cell installation/removal transitions. It stops at the explicit handoff to the normal top level.

The three-file observation patch applies only to a disposable U1 archive. `unit.py` uses the existing recoverable apply/restore mechanism. No project compiler or kernel source is patched. An observed image is evidence only; implementation starts from pristine U1 and its original bootstrap.

The recorder uses an owner-thread cons list, primitive object references and lexical bindings. It does not bind new specials before binding indices exist, retain dynamic-extent FASL state, serialize during startup, invoke an observer callback. A foreign writer sets a refusal flag. Actual old/new function objects survive GC and image save/restore; their names and source descriptions are read later and are not historical mutable metadata. Retaining those objects changes memory retention, so this is no allocation or timing measurement.

A separate first-touch binding checkpoint supplies the replay's initial state. Final bindings are read from the saved image, independently of event replay. The original cold queue is retained separately from its execution events. Each FASL initializer opcode joins the observed filename and byte offset to the actual retained file bytes. Removal events record intent immediately before the original primitive clear; an interrupted or aborted boot is not successful evidence.

The final loader, reader and initializer frames never return normally: U1 transfers into its top level, which saves the normal image. The exchange explicitly retains those three active frames at handoff. It does not fabricate their returns. All identities belong to this boot process; matching printed names do not join them to an earlier compiler process.

Run from the repository root on the reference macOS x86-64 host. Use new output directories; failed attempts are not overwritten. The evidence store supplies the pinned archives and kernel.

```sh
python3 tests/wasm/native-census/boot-observation/run.py prepare \
  --inputs /Users/buildsomething/Source/ccl-evidence/macos-u1-inputs \
  --kernel /Users/buildsomething/Source/ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --work /tmp/ccl-boot-observation-work --output /tmp/ccl-boot-observation-baseline
python3 tests/wasm/native-census/boot-observation/run.py capture \
  --inputs /Users/buildsomething/Source/ccl-evidence/macos-u1-inputs \
  --kernel /Users/buildsomething/Source/ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --work /tmp/ccl-boot-observation-work --output /tmp/ccl-boot-observation-capture
```

Preparation performs one clean build and the full native suite. Capture reuses that same unit's baseline, rebuilds with observation, compares all 164 FASLs, exports and checks the boot stream, compares evaluated native tables, runs the native suite, removes the complete patch, and rebuilds from the original bootstrap. Exactly the three instrumented FASLs may differ during observation; all 164 must match after removal. Clean executables are restored even after a failure. `test_unit.py` checks recovery and refuses a checkout, a partial patch or unexplained edits.

`test_controls.py` exercises omissions, substitutions and insertions in a genuine capture. `native-controls.lisp` additionally mutates the retained recorder state in separate native processes: active/foreign-owner states must be refused by the exporter, and a missing cold return with repaired sequence/counts must fail replay. Original logs and mutant sources belong in the same deliverable packet.

This is an execution witness for the census assembly. It does not establish complete static reachability, dynamic-call bounds, Wasm lowering, or identity equivalence across captures. The complete LL15-b/c exchange graph and independent review remain separate work.

Reproduce the retained analysis, all stream/file controls and the saved-image controls without another native build:

```sh
python3 tests/wasm/native-census/boot-observation/verify.py \
  --capture /path/to/packet/capture \
  --baseline /path/to/packet/baseline-fasls.tar.gz \
  --kernel /Users/buildsomething/Source/ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --output /tmp/ccl-boot-observation-verification
```

The verifier extracts only the supplied baseline archive into its new output directory. It maps original absolute load names through the capture's recorded source root; it never widens that root. The retained kernel is copied and made executable in the verification directory. The evidence store itself is not modified.

The retained r1 capture has 133 anonymous cold thunks: all names are NIL and all source notes are absent. Its local object identities and queue order cannot identify source forms/modules. A separate xload-side insertion witness is required for that join; until then they remain order-only census nodes with unresolved source dependencies.
