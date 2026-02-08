# WASM MVP Unattended Execution Report

Status: In Progress (RZ0.6 + runtime bootstrap closure)  
Plan: `doc/wasm/mvp-unattended-execution-plan.md`  
Last updated: 2026-02-08

## Summary

- Runtime bundle contract unification (v2), root-image manifesting, and loader
  refactor landed.
- Memory-first `memory-snapshot` persistence backend decoupling landed for the
  default unattended path.
- Root-image bootstrap/save-reload closure is now re-established for regenerated
  artifacts (`root.image` + manifest strict lane).
- Remaining MVP blocker is now compiled-Lisp UI persistence runtime execution on
  root lane: preflight entry traps with `RuntimeError: unreachable` in
  `wasm-ui-persist-smoke` after successful bootstrap/module install.

## Key command status

- `npm --prefix web-ui test`: PASS
- `node doc/wasm/js/all-smoke.mjs`: PASS
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`: PASS
- `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin`: PASS
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root`: FAIL
  at compiled UI preflight (`Lisp UI not runnable ... unreachable`) after
  contracts + module install succeed.
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

Compiled-Lisp UI persistence preflight/runtime execution on root lane is still
failing with `RuntimeError: unreachable` after:

- strict root pre-start/post-start bootstrap contract success
- runtime bundle install success
- compiled UI module install success

Resolution path (in progress):

1. Localize failing preflight callee/entry at runtime trap boundary.
2. Reconcile emitted UI module function bindings/spec forms with runtime
   callable expectations in root lane.
3. Re-run `wasm-ui-persist-smoke` under default `memory-snapshot` backend and
   close the trap class in regression gates.

## Next execution gate

Close runtime bootstrap blocker tracked in
`doc/wasm/wasm-ui-persistence-problem-tracker.md`, then run:

```bash
npm --prefix web-ui test
node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive
CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs
node doc/wasm/js/all-smoke.mjs
```
