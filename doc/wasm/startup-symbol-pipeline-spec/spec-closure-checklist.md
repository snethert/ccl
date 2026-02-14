# Spec Closure Checklist (Actionable)

Use this checklist to verify whether the spec is complete enough for direct,
uninterrupted implementation.

Status legend:
- `[ ]` missing
- `[x]` fully specified in spec

Implementation note:
- This checklist is spec-completeness first.
- Implementation closure is tracked separately in:
  - `doc/wasm/startup-symbol-pipeline-spec/contradiction-ledger.md` (C-001..C-012)
  - `doc/wasm/startup-symbol-pipeline-implementation-plan.md` Section `19` gates
    (`G-01`..`G-12`)
  - `doc/wasm/startup-symbol-pipeline-implementation-plan.md` Section `22`
    execution cards (`M-001`..`M-067`)
- Execution status snapshot (2026-02-14):
  - `G-11` passed via `M-063` (legacy-path grep gate).
  - `G-12` remains pending until `M-067`.
  - Evidence pointers:
    - `doc/wasm/startup-symbol-pipeline-implementation-plan.md` Section `22` cards
      `M-061`, `M-062`, `M-063`, `M-064`.
    - `doc/wasm/startup-symbol-pipeline-spec/contradiction-ledger.md` closure evidence bullets.

## A. Artifact Contracts

- [x] Scope artifact full schema locked.
- [x] Resolution artifact full schema locked.
- [x] Map/shadow compatibility contract locked.
- [x] Deterministic hash rules locked.
- [x] Canonical path rules locked.

## B. Scanner Contracts

- [x] Contract sidecar generation format locked.
- [x] Feature profile mapping table locked.
- [x] Reader environment and failure policy locked.
- [x] Role extraction grammar locked.
- [x] Scanner CLI + exit code contract locked.

## C. Runtime Contracts

- [x] Resolver authority and staging locked.
- [x] Required-class mapping locked.
- [x] Entry synthesis matrix locked.
- [x] Apply initializer ABI for symbol/keyword literals locked.
- [x] Preinstall budget formula constants locked.

## D. Pipeline Contracts

- [x] Compile pipeline step insertion locked.
- [x] `M-021` semantic wiring checks locked (required flags + ordering + fail-fast guard; not grep-only).
- [x] Repro pipeline step insertion locked.
- [x] make-real-image CLI propagation locked.
- [x] make-real-image.lisp forwarding contract locked.
- [x] Packaging behavior (no JS source scan) locked.

## E. Diagnostics And Validation

- [x] `STARTUP_SYMBOL_PIPELINE` schema locked.
- [x] `STARTUP_SYMBOL_SCOPE_BUILD` schema locked.
- [x] `STARTUP_SYMBOL_RESOLUTION_BUILD` schema locked.
- [x] Validation script expected key set locked.
- [x] Boundary and memory assertion conditions locked.

## F. Manifest And Auditability

- [x] Repro manifest artifact hash coverage locked.
- [x] Root manifest inclusion/exclusion policy for startup artifacts locked.
- [x] Schema bump strategy locked.
- [x] Evidence bundle schema locked.

## G. Migration And Cleanup

- [x] Legacy compatibility horizon locked.
- [x] Legacy env flags removal list locked.
- [x] Single-path grep assertions locked.
- [x] Build docs architecture replacement locked.

## H. Contradiction Closure

- [x] C-001 decision locked.
- [x] C-002 decision locked.
- [x] C-003 decision locked.
- [x] C-004 decision locked.
- [x] C-005 decision locked.
- [x] C-006 decision locked.
- [x] C-007 decision locked.
- [x] C-008 decision locked.
- [x] C-009 decision locked.
- [x] C-010 decision locked.
- [x] C-011 decision locked.
- [x] C-012 decision locked.
- [ ] C-001 implementation closed.
- [ ] C-002 implementation closed.
- [ ] C-003 implementation closed.
- [ ] C-004 implementation closed.
- [ ] C-005 implementation closed.
- [ ] C-006 implementation closed.
- [ ] C-007 implementation closed.
- [ ] C-008 implementation closed.
- [ ] C-009 implementation closed.
- [ ] C-010 implementation closed.
- [ ] C-011 implementation closed.
- [ ] C-012 implementation closed.

## I. Gate Closure (Execution Control)

- [ ] `G-01` parser path isolation gate passed.
- [ ] `G-02` schema lock gate passed.
- [ ] `G-03` scanner implementation gate passed.
- [ ] `G-04` compile/repro integration gate passed.
- [ ] `M-021.1`..`M-021.4` semantic substeps passed.
- [ ] `G-05` resolver gate passed.
- [ ] `G-06` map synthesis gate passed.
- [ ] `G-07` initializer expansion gate passed.
- [ ] `G-08` preinstall budget gate passed.
- [ ] `G-09` focused lane validation gate passed.
- [ ] `G-10` repro validation gate passed.
- [x] `G-11` legacy path removal gate passed.
- [ ] `G-12` evidence bundle gate passed.
- [ ] `G-13` startup stub-dependency gate passed.

## J. Handoff Prompt Contract

- [x] Canonical template path is locked: `doc/wasm/startup-symbol-next-session-prompt-template.md`.
- [x] Stop reasons restricted to `blocked_dependency` or explicit `user_decision` only.
- [x] `objective_complete` is explicitly forbidden as a standalone stop reason.
- [x] Every terminal response must include inline copy-paste `NEXT_SESSION_PROMPT`.
- [x] `TERMINATION_CHECKLIST` schema and required keys are locked.
- [x] `BLOCKED_REPORT_FORMAT` schema is locked for all blocked stops.

## K. Resume Closure Recompute Verification

- [x] Checked-in verifier exists: `scripts/wasm/recompute-resume-closure-matrix.sh`.
- [x] Positive parity command is locked:
  - `scripts/wasm/recompute-resume-closure-matrix.sh --output-prefix /private/tmp/step93.doccheck`
- [x] Positive expected outcome is locked:
  - exit code `0`
  - all `/private/tmp/step93.doccheck.diff.*` files are zero bytes
- [x] Negative mismatch command is locked:
  - `scripts/wasm/recompute-resume-closure-matrix.sh --output-prefix /private/tmp/step93.doccheck.negative --log /private/tmp/make-real-image.resume.applycontinue.reqfasload9.trace.log`
- [x] Negative expected outcome is locked:
  - exit code is non-zero
  - at least one `/private/tmp/step93.doccheck.negative.diff.*` file is non-zero
