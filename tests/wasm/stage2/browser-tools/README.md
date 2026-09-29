# Stage 2 browser toolchain

The qualified matrix uses **playwright-core 1.58.0**, Chromium **145.0.7632.6**
(`chromium-1208`), Firefox **146.0.1** (`firefox-1509`) and WebKit **26.0**
(`webkit-2248`). Playwright 1.55 fails with this WebKit revision; audit 197 O-175
reproduces the mismatch. The package and integrity lock here survive RAM resets.

Recreate the Node driver on verified RAM storage from the repo root:

```sh
tools=/private/tmp/ccl-work/codex/stage2-browser-tools
mkdir -p "$tools"
cp tests/wasm/stage2/browser-tools/package*.json "$tools/"
npm ci --prefix "$tools" --ignore-scripts --no-audit --no-fund \
  --cache /Users/buildsomething/Library/Caches/ccl-wasm-validation/npm
```

Pass `"$tools/node_modules/playwright-core/index.mjs"` as `--playwright`.
The browsers have their own persistent installation under
`~/Library/Caches/ms-playwright`; pass a `--browser-config` JSON mapping
`chromium`, `firefox`, and `webkit` to their executable paths. Every qualification
pack retains that mapping and executable hashes. If missing, install the three
revisions with this pinned package's `cli.js install chromium firefox webkit`.
The runner records actual versions and SHA-256 hashes; do not silently substitute
other browser revisions for a reproduction claim.
