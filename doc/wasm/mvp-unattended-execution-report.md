# WASM MVP Unattended Execution Report

Status: Completed (2026-02-08)
Plan: `doc/wasm/mvp-unattended-execution-plan.md`

## Command Summary

- `npm --prefix web-ui test`: PASS
- `scripts/wasm/compile-smoke-modules.sh --output doc/wasm/wasm-smoke-modules.json`: PASS
- `node doc/wasm/js/compiler-smoke.mjs`: PASS
- `node doc/wasm/js/runtime-command-smoke.mjs`: PASS
- `node doc/wasm/js/closure-unwind-mv-smoke.mjs`: PASS
- `node doc/wasm/js/mvcall-smoke.mjs`: PASS
- `scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json`: PASS
- `node doc/wasm/js/start-lisp-smoke.mjs`: PASS
- `scripts/wasm/compile-ui-modules.sh --output doc/wasm/wasm-ui-modules.json`: PASS
- `node doc/wasm/js/web-ui-command-ui-smoke.mjs`: PASS
- `node doc/wasm/js/all-smoke.mjs`: PASS
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs`: SKIP (default non-strict mode)

## Implemented Changes

- Fixed compiler-smoke FFI regression (`ffi-add`) by synchronizing VSP state in test funcall helper paths (`lisp-kernel/wasm-kernel-stubs.c`).
- Added FFI regression coverage for signed and zero argument marshalling in `doc/wasm/js/compiler-smoke.mjs`.
- Hardened spill discipline enforcement:
  - `multiple-value-call` now spills around `.SPfuncall` calls.
  - `:call-subprim-no-spill` is now allowlisted and validated.
  - Spill depth is validated to end balanced.
- Added explicit spill/restore invariants in `doc/wasm/ABI.md`.
- Updated smoke fixture for closure/unwind/mv to keep allocation + unwind + MV>4 coverage while avoiding the deadlocking shape.
- Rebuilt smoke/runtime/UI module bundles and kernel artifacts.
- Reconciled stale status docs (roadmap, porting status, testing docs, front-end plan, and affected phase-5 web-ide docs).

## Deferred / Remaining

- Strict compiled-Lisp UI persistence runtime path remains opt-in:
  - Run with `node doc/wasm/js/wasm-ui-persist-smoke.mjs --strict`.
  - Default mode skips to keep unattended sandbox runs deterministic.
