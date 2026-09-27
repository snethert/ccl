# Module-archive measurement and prototype scripts

Support for `doc/WASM/stage1/module-consolidation-plan.md` (MCP-P1). These are
measurement instruments, not product code or a proposed implementation. They
read the retained loader inputs (a `bundles-*` directory with
`bundle-manifest.json`, `*.records.json`, `*.w32bundle`, `policy.json`,
`versions.json`, and a boot `code-set.json` with per-module WAT) and print JSON.

| script | measures | invocation |
|---|---|---|
| `stats.mjs` | files, units, modules, bytes, import inventory per module | `node stats.mjs <bundles-dir>` |
| `helpers.mjs` | entry-body bytes versus total bytes (helper fraction), largest files | `node helpers.mjs <bundles-dir>` |
| `dedupe.mjs` | helper function bodies, distinct bodies by content | `node dedupe.mjs <bundles-dir>` |
| `cost.mjs` | per-stage admission cost of the v1 path on one bundle | `node cost.mjs <bundles-dir> <stem>` |
| `merge.mjs` | prototype WAT linker: one module per tier, helpers deduplicated, symbol/code imports renamed per function | `node --max-old-space-size=12288 merge.mjs <out.wat> bundle\|boot <records.json or code-set.json>...` |
| `engine.mjs` | validate, compile, instantiate and table publication of a merged module | `node engine.mjs <out.wasm>` (reads `<out>.wat.imports.json`) |

Assemble a merged WAT with the pinned WABT: `wat2wasm --enable-all out.wat -o out.wasm`.
`merge.mjs` emits the template form (unshared memory); `engine.mjs` therefore
imports an unshared memory. Results from 27 September 2026 on boot-r21 and
bundles-r18 are in `measurements.json`.
| `admit-all.mjs` | v1 admission of every bundle kept alive: time and process memory | `node --max-old-space-size=16384 admit-all.mjs <bundles-dir>` |
