# Step 09-12 Validation, Repro, Cleanup, Documentation Spec

This document specifies the final four steps needed to land the compromise
without ambiguity.

## Step 09: Focused Lane Validation (top4488 + smoke)

### Immediate Problems

1. Planned commands reference options and diagnostics not implemented yet
   (`--startup-symbol-scope`, `STARTUP_SYMBOL_*` lines).

2. No machine-readable validator currently checks all required assertions in one
   pass.

3. Existing logs focus on `STARTUP_BINDING_MAP_*`; new scope/resolution
   diagnostics are absent.

### Required Additional Spec

- `S9.1` Exact command templates after CLI wiring is complete.
- `S9.2` Required log JSON keys for each diagnostic line.
- `S9.3` Pass/fail assertion script contract (input logs -> exit code + summary).

### Recommended Defaults To Unblock

- Add a small verifier script (shell or Node) that checks:
  - startup pipeline mode line,
  - scope build line,
  - resolution build line,
  - map apply pass,
  - L0 contract pass,
  - absence of memory failure signatures.

## Step 10: Full Repro Pipeline Validation

### Immediate Problems

1. `repro-startup-pipeline.sh` does not currently generate or track scope
   artifact.

2. Run manifest artifact list omits startup scope/resolution artifacts.

3. Step ordering does not enforce scanner-before-`make-real-image`.

### Required Additional Spec

- `S10.1` New repro steps and canonical names.
- `S10.2` Run manifest schema update (`schemaVersion` bump policy).
- `S10.3` Artifact retention policy for scanner logs and generated JSON.

### Recommended Defaults To Unblock

- Add repro step `collect-startup-symbol-scope` after
  `compile-runtime-modules` and before `make-root-image`.
- Record scope artifact and optional resolution artifact in manifest `artifacts`
  with size + sha256.
- Fail pipeline immediately when scanner step exits non-zero.

## Step 11: Legacy Path Removal And Cleanup

### Immediate Problems

1. Legacy behavior is spread across runtime, pack, compact scripts, and docs.

2. Current removal list in plan is not exhaustive; JS scanner helpers and bundle
   generation fallback paths remain potential re-entry points.

3. No concrete grep checklist exists for final single-path verification.

### Required Additional Spec

- `S11.1` Exhaustive deletion/deactivation list:
  - flags,
  - code paths,
  - exports,
  - docs.

- `S11.2` Compatibility horizon:
  - date/commit criterion for removing legacy compatibility branch.

- `S11.3` Final grep assertions used in CI.

### Recommended Defaults To Unblock

- Define and execute a removal checklist including:
  - legacy emit-all-functions environment toggles,
  - JS source scanner functions in `startup-binding-map.mjs`,
  - map generation fallback in `make-real-image.mjs`,
  - stale build.md architecture sections describing JS scanner ownership.

## Step 12: Documentation And Audit Evidence Bundle

### Immediate Problems

1. Current docs still describe JS-owned startup binding artifact generation.

2. No standard evidence bundle format is defined, so final review quality is
   inconsistent.

3. No explicit done criteria ties code search, diagnostics, and repro outputs
   together.

### Required Additional Spec

- `S12.1` Required documentation updates and exact sections to replace.
- `S12.2` Evidence bundle schema (files, log excerpts, counts, hashes).
- `S12.3` Reviewer checklist mapped to concrete command outputs.

### Recommended Defaults To Unblock

- Add an evidence manifest file per run under `doc/wasm/repro/...` containing:
  - command list,
  - artifact hashes,
  - key diagnostic excerpts,
  - required assertion outcomes.
- Update `doc/wasm/build.md` to make the Common Lisp scanner + artifact-first
  model the only documented active architecture.
