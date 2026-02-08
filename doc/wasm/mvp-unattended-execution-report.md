# WASM MVP Unattended Execution Report

Status: In Progress (RZ0 pass, 2026-02-08)
Plan: `doc/wasm/mvp-unattended-execution-plan.md`

## Command Summary

- `git status --short`: PASS (captured baseline dirty worktree)
- `npm --prefix web-ui test`: PASS
- `node doc/wasm/js/all-smoke.mjs`: PASS
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs`: FAIL (compiled module const-pool install error on root image, entry 320)
- `node doc/wasm/js/load-image.mjs --start-lisp --modules doc/wasm/wasm-runtime-modules.json doc/wasm/root.image`: FAIL before RZ0.2 (legacy runtime bundle format mismatch)
- `scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json`: PASS
- `scripts/wasm/build-wasm-boot.sh`: PASS
- `node doc/wasm/js/make-real-image.mjs --modules doc/wasm/wasm-runtime-modules.json --output doc/wasm/root.image`: PASS
- `node doc/wasm/js/runtime-modules-manifest-smoke.mjs`: PASS
- `node doc/wasm/js/root-image-manifest-smoke.mjs`: PASS
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs`: PASS (strict-root check intentionally skipped by default)
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`: FAIL (timeout after 15000ms)
- `node doc/wasm/js/all-smoke.mjs`: PASS
- `npm --prefix web-ui test`: PASS

## Implemented Changes

- Runtime bundle contract unified to v2 on the default build path:
  - `scripts/wasm/compile-wasm-fasls.sh` now repacks inline output through `scripts/wasm/pack-inline-bundle-v2.mjs`.
  - Temp inline sidecars are cleaned after pack.
- Added runtime artifact validation smoke:
  - `doc/wasm/js/runtime-modules-manifest-smoke.mjs`
  - wired into `doc/wasm/js/all-smoke.mjs`.
- Added root-image manifest contract:
  - `doc/wasm/root-image-manifest.schema.json`
  - `doc/wasm/js/make-real-image.mjs` now writes `<output>.manifest.json` by default (or `--manifest-out`).
  - `scripts/wasm/make-real-image.lisp` now forwards `--manifest-out` to the Node helper path.
- Added root-image manifest validation smoke:
  - `doc/wasm/js/root-image-manifest-smoke.mjs`
  - wired into `doc/wasm/js/all-smoke.mjs`.
- Refactored `doc/wasm/js/load-image.mjs`:
  - explicit `--mode boot-only|start-lisp|run-toplevel`
  - compatibility aliases `--start-lisp` / `--run`
  - manifest hash validation (`--manifest`)
  - strict/partial module policy controls (`--strict-modules`, `--allow-partial-modules`)
  - non-interactive stdin preload controls (`--stdin-script`, `--stdin-text`, `--close-stdin`)
  - entry return code assertions (`--expect-rc`).
- Added hang-proof start-lisp harness:
  - `doc/wasm/js/start-lisp-noninteractive-smoke.mjs`
  - wired into `doc/wasm/js/all-smoke.mjs` with strict-root check opt-in via `--strict-start-lisp-noninteractive`.
- Browser harness root-image preference landed:
  - `web-ui/tests/browser/harness.mjs` now attempts `doc/wasm/root.image` first, then falls back to `doc/wasm/minimal.image`.
- Docs reconciled to current behavior:
  - `doc/wasm/image-loader-spec.md`
  - `doc/wasm/build.md`
  - `doc/wasm/roadmap.md`
  - `doc/wasm/porting-status.md`.

## Deferred / Remaining

1. Strict root-image non-interactive `start_lisp` still blocks:
   - `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`
   - Current result: timeout after 15000ms.
2. Compiled-Lisp UI persistence runtime path is still unstable on root image:
   - `node doc/wasm/js/wasm-ui-persist-smoke.mjs`
   - Current result: `const pool install returned NIL for entry 320` (`ccl_generic_entry_320`).
