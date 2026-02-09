# WASM MVP Unattended Execution Report

Status: In Progress (RZ0.6 blocker trap closure + persistence semantics follow-through)  
Plan: `doc/wasm/mvp-unattended-execution-plan.md`  
Last updated: 2026-02-09

## Summary

- Runtime bundle contract unification (v2), root-image manifesting, and loader
  refactor landed.
- Memory-first `memory-snapshot` persistence backend decoupling landed for the
  default unattended path.
- Root-image bootstrap/save-reload closure is now re-established for regenerated
  artifacts (`root.image` + manifest strict lane).
- Root-lane compiled-Lisp UI persistence preflight/runtime trap is closed by
  moving UI module entries to a deterministic in-memory state-machine path
  (no fragile core-symbol call dependencies).
- Remaining MVP work is to finish persistence semantics integration:
  wire UI save/restore to documented memory-snapshot service behavior.

## Key command status

- `npm --prefix web-ui test`: PASS
- `node doc/wasm/js/all-smoke.mjs`: PASS
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`: PASS
- `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin`: PASS
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root`: PASS
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image minimal`: FAIL
  strict pre-start contract (expected bring-up lane).

## Implemented foundations (already landed)

- Runtime module bundle contract:
  - `ccl-wasm-modules-v2` manifest + `.bin` + `.idx`
  - emitted by default from `scripts/wasm/compile-wasm-fasls.sh`
- Runtime module manifest smoke:
  - `doc/wasm/js/runtime-modules-manifest-smoke.mjs`
- Root-image manifest contract:
  - `doc/wasm/root-image-manifest.schema.json`
  - `doc/wasm/root.image.manifest.json` generation in `doc/wasm/js/make-real-image.mjs`
- Root-image manifest smoke:
  - `doc/wasm/js/root-image-manifest-smoke.mjs`
- Loader contract refactor:
  - explicit `--mode boot-only|start-lisp|run-toplevel`
  - `--manifest`, `--strict-modules`, `--allow-partial-modules`
  - scripted stdin controls and return-code checks
- Hang-proof non-interactive start-lisp harness:
  - `doc/wasm/js/start-lisp-noninteractive-smoke.mjs`

## Active blocker (current)

Persistence semantics completion after trap closure:

- root-lane smoke now passes, but current UI save/restore behavior is process-
  local state-machine persistence.
- next step is full alignment with memory-snapshot contract (in-memory runtime
  store + dirty flush policy) for UI persistence actions.

## Next execution gate

Close remaining persistence semantics and dispatch hardening items tracked in
`doc/wasm/wasm-ui-persistence-problem-tracker.md`, then run:

```bash
npm --prefix web-ui test
node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive
CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs
node doc/wasm/js/all-smoke.mjs
```
