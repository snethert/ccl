# Audit 181: reviewed loader stack integration

Audit `973c10bb` is imported unchanged. The reviewer found no defect in the
three-proposal stack (`e2de2fd9`, `928ad5ef`, `d2841e95`) above audit 180's
integration. The user's instruction to proceed and the supplied conditional
integration recommendation are recorded in
[`integration-loader-stack.json`](../../../../doc/WASM/stage1/integration-loader-stack.json).
Eight final product files are integrated byte-for-byte from those reviewed
proposals. No compiler or runtime behavior is changed by this follow-up.

`check.py` verifies all eight reviewed copies, all 43 qualified compiler/CCL
source inputs, runtime inputs, the imported review prefix and the immutable
qualification records. Native R6/R6a (21,843 tests, 164 restored FASLs), the 68
reader comparisons (34 pointer and 34 definitions), 26,048 corpus comparisons, and the 46-check array collector
qualification are reused by exact identity. These are reused results, not new
native/corpus runs. The final definitions packet binds the actual corpus
collector; the pointer packet's earlier discrepancy remains disclosed.

The new harness execution compiles the integrated source set, loads eleven
complete production FASLs after deleting their source files, and compares 111
observations with native in four placement/collection modes. It retains the
595 modules, 33 initializers and all 116 runtime controls. Each old observation
must match the reviewed packet. All eleven production FASLs must be byte-equal
to that packet; support FASLs and their dependent image change with the witness.
A separate Git-free, different-root replay compares every generated Wasm FASL, heap,
WAT and Wasm artifact and all final results. Final drivers are bound before and
after execution and checked at retention.

The final run passes all 111 comparisons and 116 controls in each mode, with
9/151 collections. M1 is killed by the new observation in all four modes while
the old 110 remain equal. All 1,825 replayed Wasm FASL/heap/WAT/Wasm artifacts
are byte-identical; 2,997 regenerable artifacts still match the original reviewed
packet, including all eleven production FASLs. The retained development record
explains the initial wrong mutant expectation and replay import collision.

## Audit dispositions

- **O-92 — open before level-1 CLOS boot.** `COPY-METHOD-FUNCTION-BITS` in
  `level-1/l1-clos-boot.lisp:630-641` writes ordinary compiled functions through
  `LFUN-BITS`; callers occur at lines 313 and 777, in `level-1/l1-clos.lisp:959`,
  and in `lib/encapsulate.lisp:538,790,893`. The present Wasm setter refuses
  ordinary functions. Before boot, implement writable metadata or an explicit
  target implementation preserving method/next-method/argument bits, and qualify
  method construction and dispatch against native. Current funcallable-instance
  writes and ordinary-function refusal controls do not close this obligation.
- **O-93 — closed by the reviewed definitions packet.** The original pointer
  evidence stays immutable. Only the later corpus qualifies the array-collector
  combination; its executed binary digest is asserted against the loader.
- **O-94 — added branch witness.** `float-subnormal-10` decodes
  `(scale-float 1.0d0 -1030)`: fraction 0.5, exponent -1029, positive sign,
  precision 45. The reviewer's M1 changes `(- 20 (integer-length high))` to
  `(- 21 ...)`. A separate disposable producer must leave the old 110 rows
  equal and fail only this new row in all four modes (exponent -1030,
  precision 44; fraction remains 0.5). Mutant runs have no product credit.
- **O-95 — carried range limit.** `%%SCALE-SFLOAT!` masks the exponent to eight
  bits while native LAP does not. In-range behavior agrees. Out-of-range helper
  calls and the full numerical library remain unqualified.
- **O-96 — anchored.** Both exercise drivers call one checked helper for the
  manifest capacity, two table constructors and the registry header. An unrelated
  literal is preserved; missing and duplicate anchors refuse. Host-selected
  absolute scratch/image addresses remain temporary scaffolding under O-70/O-77.

The ordered compiler still completes nine level-0 files and stops at
`:EQ-VECTOR-INITIAL-ELEMENT` in `l0-hash`. O-90's duplicate integer-definition
cleanup remains separate. Production counts **0/0/0**, original executions
**575/535**, and ledger **21/12** stay unchanged. No target LOAD or boot credit.
The product integration is covered by audit 181; these additional harness
checks remain available for the next adversarial review.

```sh
python3 tests/wasm/stage1/loader-stack-acceptance/check.py
python3 tests/wasm/stage1/loader-stack-acceptance/run.py /private/tmp/ccl-work/codex/loader-stack-integration/run
python3 tests/wasm/stage1/loader-stack-acceptance/run.py /private/tmp/ccl-work/codex/loader-stack-mutant/run --mutant
python3 tests/wasm/stage1/loader-stack-acceptance/replay.py /private/tmp/ccl-work/codex/loader-stack-replay/run /private/tmp/ccl-work/codex/loader-stack-integration/run
python3 tests/wasm/stage1/loader-stack-acceptance/retain.py /private/tmp/ccl-work/codex/loader-stack-integration/run /private/tmp/ccl-work/codex/loader-stack-mutant/run /private/tmp/ccl-work/codex/loader-stack-replay/run /private/tmp/ccl-work/codex/loader-stack-development/run /Users/buildsomething/Source/ccl-evidence/2026-09-25-loader-stack-integration
```

The superseded isolated drivers retain their original integrated-base contract.
Use this successor driver with the current checkout; historical runs remain
reproducible from their recorded revisions. Retention leaves prior packets
unchanged and removes disposable outputs only after verifying the new packet.
