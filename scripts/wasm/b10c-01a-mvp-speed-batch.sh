#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/b10c-01a-mvp-speed-batch.sh [--refresh-a18] [--no-prune]

Batch mode:
- Applies deterministic A01..A16 speed-prune pass (default on)
- Enforces A01..A16 hardening gate
- Refreshes A17 checkpoint with strict speed bounds
- Optionally refreshes A18 fallback artifact
- Runs required validation flow once at the end (exact order)
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

REFRESH_A18=0
DO_PRUNE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --refresh-a18)
      REFRESH_A18=1
      shift
      ;;
    --no-prune)
      DO_PRUNE=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

A17_ARTIFACT="doc/wasm/tickets/evidence/bpl-10/b10c-01a-17-fixnum-add-checkpoint-2026-02-10.json"
A18_ARTIFACT="doc/wasm/tickets/evidence/bpl-10/b10c-01a-18-misc-set-fallback-checkpoint-2026-02-10.json"

if [[ "${DO_PRUNE}" -eq 1 ]]; then
  node scripts/wasm/b10c-01a-mvp-speed-prune.mjs
fi

node scripts/wasm/b10c-01a-hardening-gate.mjs

node doc/wasm/js/fixnum-add-smoke.mjs \
  --perf-checkpoint \
  --perf-samples 3 \
  --perf-budget-delta-ns 0 \
  --perf-max-direct-helper-calls-per-op 0 \
  --perf-out "${A17_ARTIFACT}"

if [[ "${REFRESH_A18}" -eq 1 ]]; then
  node doc/wasm/js/misc-set-fallback-smoke.mjs \
    --checkpoint \
    --iterations 20000 \
    --max-misc-set-calls-per-op 1 \
    --checkpoint-out "${A18_ARTIFACT}"
else
  [[ -f "${A18_ARTIFACT}" ]] || {
    echo "FAIL: missing required A18 baseline artifact: ${A18_ARTIFACT}" >&2
    exit 1
  }
fi

/bin/zsh -lc 'source scripts/wasm/env.sh && make -C lisp-kernel/wasm32 CC="$CC" WASM_LD="$WASM_LD"'
scripts/wasm/arm-retirement-audit.sh --strict
/bin/zsh -lc 'source scripts/wasm/env.sh && node doc/wasm/js/make-real-image.mjs --boot-image wasm-boot.image --modules doc/wasm/wasm-runtime-modules.json --output doc/wasm/root.image --manifest-out doc/wasm/root.image.manifest.json'
node doc/wasm/js/all-smoke.mjs

node -e 'const fs=require("fs"); const p=process.argv[1]; const j=JSON.parse(fs.readFileSync(p,"utf8")); const before=(j.lanes?.beforeCompat?.dynamicPath?.callsPerOperation?.wasm_return_fixnum_add ?? 0); const after=(j.lanes?.afterDirect?.dynamicPath?.callsPerOperation?.wasm_return_fixnum_add ?? 0); const d=j.deltas?.latencyNsPerOp; const pct=j.deltas?.latencyPct; console.log(`A17: delta=${d}ns/op (${pct}%), wasm_return_fixnum_add calls/op ${before}->${after}`);' "${A17_ARTIFACT}"

echo "PASS: B10C-01A-01..A-16 MVP speed batch completed"
