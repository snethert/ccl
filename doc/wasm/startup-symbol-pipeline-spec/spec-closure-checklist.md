# Spec Closure Checklist (Actionable)

Use this checklist to verify whether the spec is complete enough for direct,
uninterrupted implementation.

Status legend:
- `[ ]` missing
- `[x]` fully specified in spec (implementation may still be pending)

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

- [ ] C-001 closed.
- [ ] C-002 closed.
- [ ] C-003 closed.
- [ ] C-004 closed.
- [ ] C-005 closed.
- [ ] C-006 closed.
- [ ] C-007 closed.
- [ ] C-008 closed.
- [ ] C-009 closed.
- [ ] C-010 closed.
- [ ] C-011 closed.
- [ ] C-012 closed.
