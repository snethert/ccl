# Audit 138: portable replay and bounded admission

Auxiliary follow-up to `0406237d`. No runtime, compiler, service source or service binary changes. No LL15 credit or acceptance. Original packets and fixtures remain intact.

The verifier records checkout dependencies as `ROOT/<relative path>`, evidence dependencies as `EVIDENCE/<relative path>`, and executable dependencies under `TOOL/<absolute path>`. It binds the original dependency file by hash and checks its full contents after translating exactly the two old checkout keys and the evidence prefix. Source pins and digests remain mandatory. This verifier supersedes the checkout-specific verification entry for audit 137 and reruns all 258 deterministic files, including native compilation and Chromium execution. It must also pass from a detached worktree, using that worktree's source paths.

The additional probes isolate the cons depth guard and the separate numeric depth guard. EQL and EQUAL run complex-tagged chains at depths 1022, 1023, 1024 and 3000 below and above 2 GiB. The first two exercise the fixed array boundary; the latter two must refuse status 3 without changing key, table or publication. Deep numeric graphs are malformed-owner inputs, not newly admitted Lisp numeric semantics. Cons depth controls apply only to EQUAL.

Five directed bounds refusals cover unbacked population objects, result regions and list keys, and unbacked cons and header keys in both table modes. The result-region case performs SET and offers only eight backed bytes: the population must remain unchanged before any result store. A trap is explicitly reported as a test failure, never accepted as a checked refusal. Each guard has a separately recompiled omission control. The static C-stack header check also gets an opaque-header case, independent of the inspected-object overlap guard; its omission is **not** assumed equivalent merely because a double-float probe is caught elsewhere.

`admission-clauses.json` maps admission clauses to directed refusals or explicit equivalence arguments and names their retained sources. Four older population clauses are additionally isolated here (header, type range, padding and key tag). The six audit-137 guards and original native/movement checks are replayed. Services are copied from that exact execution, with unchanged hashes. The already redundant base-alignment trim continues to produce the original population binary.

Run and retain:

```
python3 tests/wasm/stage1/startup-review-138/run.py --output /new/execution
python3 tests/wasm/stage1/startup-review-138/packet.py retain --execution /new/execution --packet ../ccl-evidence/2026-09-21-stage1-startup-review-138-r1
```

Replay (also from a detached checkout):

```
python3 tests/wasm/stage1/startup-review-138/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-startup-review-138-r1 --output /new/replay
```

Only the new files are duplicated in this packet; parent deterministic execution is checked against the immutable prior packet rather than recopied. Native R6/R6a and unchanged population-native answers are reused by the parent bindings. Parent scope exclusions and all actual bootstrap installation/READY joins remain open. This unit does not qualify the complete LL15 worklist.
