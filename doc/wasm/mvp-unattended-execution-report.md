# WASM MVP Unattended Execution Report

Status: In Progress (RZ0.6 + runtime bootstrap closure)  
Plan: `doc/wasm/mvp-unattended-execution-plan.md`  
Last updated: 2026-02-08

## Summary

- Runtime bundle contract unification (v2), root-image manifesting, and loader
  refactor landed.
- Memory-first `memory-snapshot` persistence backend decoupling landed for the
  default unattended path.
- Remaining MVP blocker is now runtime bootstrap state for compiled-Lisp
  persistence entries: key function bindings are still unresolved in current
  image state, causing entry-call hangs in `wasm-ui-persist-smoke`.

## Key command status

- `npm --prefix web-ui test`: PASS
- `node doc/wasm/js/all-smoke.mjs`: PASS
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`: PASS
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs`: FAIL/HANG on compiled entry
  execution after module install; active root-cause details are tracked in
  `doc/wasm/wasm-ui-persistence-problem-tracker.md`.

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

Compiled-Lisp persistence entries still depend on runtime bootstrap function
bindings that are not available in current loaded image state
(for example, unresolved function constants for symbols like
`COMMON-LISP::CAR`, `CCL::SET-PACKAGE`, `CCL::%FASLOAD`).

Resolution path (in progress):

1. Complete runtime bootstrap sequencing fix (boot image load/reset/install order
   + entry execution prerequisites).
2. Finish root-image initialization path so required function cells are defined
   before persistence entry probes execute.
3. Re-run `wasm-ui-persist-smoke` under default `memory-snapshot` backend and
   close hang class in regression gates.

## Next execution gate

Close runtime bootstrap blocker tracked in
`doc/wasm/wasm-ui-persistence-problem-tracker.md`, then run:

```bash
npm --prefix web-ui test
node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive
CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs
node doc/wasm/js/all-smoke.mjs
```
