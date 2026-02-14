#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DRYRUN=0
FORCE=0
TRACE=0
MODULES_OUT=""
MODULES_DEBUG_OUT=""
COMPACT_RUNTIME_MODULES=0
STRIP_RUNTIME_FUNCTIONS=1

usage() {
  cat <<'EOF'
Usage: scripts/wasm/compile-wasm-fasls.sh [options]

Options:
  --force        Recompile even if fasls are up to date
  --trace-modules Print module names as they are processed
  --modules-out PATH Write compiled module bundle JSON to PATH
  --modules-debug-out PATH Write compiled module debug JSON to PATH
  --compact-runtime-modules Compact runtime module bundle after packing
  --no-strip-runtime-functions Keep functions[] in compacted runtime manifest
  --dry-run      Print commands without executing
  -h, --help     Show this help
EOF
}

run() {
  if [ "$DRYRUN" -eq 1 ]; then
    printf '+ %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

while [ "${1:-}" != "" ]; do
  case "$1" in
    --force) FORCE=1 ;;
    --trace-modules) TRACE=1 ;;
    --modules-out)
      MODULES_OUT="${2:-}"
      if [ -z "$MODULES_OUT" ]; then
        echo "error: --modules-out requires a path" >&2
        exit 1
      fi
      shift
      ;;
    --modules-debug-out)
      MODULES_DEBUG_OUT="${2:-}"
      if [ -z "$MODULES_DEBUG_OUT" ]; then
        echo "error: --modules-debug-out requires a path" >&2
        exit 1
      fi
      shift
      ;;
    --compact-runtime-modules) COMPACT_RUNTIME_MODULES=1 ;;
    --no-strip-runtime-functions) STRIP_RUNTIME_FUNCTIONS=0 ;;
    --dry-run) DRYRUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if [ -n "${CCL_BIN:-}" ]; then
  if [ ! -x "$CCL_BIN" ] && ! command -v "$CCL_BIN" >/dev/null 2>&1; then
    echo "error: CCL_BIN is set but not executable: $CCL_BIN" >&2
    exit 1
  fi
else
  CCL_BIN="$ROOT_DIR/dx86cl64"
  if [ ! -x "$CCL_BIN" ]; then
    if command -v ccl >/dev/null 2>&1; then
      CCL_BIN="ccl"
    else
      echo "error: ccl not found in PATH and $ROOT_DIR/dx86cl64 is missing" >&2
      exit 1
    fi
  fi
fi

SCRIPT="$ROOT_DIR/scripts/wasm/compile-wasm-fasls.lisp"
if [ ! -f "$SCRIPT" ]; then
  echo "error: missing $SCRIPT" >&2
  exit 1
fi

PACK_SCRIPT="$ROOT_DIR/scripts/wasm/pack-inline-bundle-v2.mjs"
if [ ! -f "$PACK_SCRIPT" ]; then
  echo "error: missing $PACK_SCRIPT" >&2
  exit 1
fi

COMPACT_SCRIPT="$ROOT_DIR/scripts/wasm/compact-runtime-modules.mjs"
if [ "$COMPACT_RUNTIME_MODULES" -eq 1 ] && [ ! -f "$COMPACT_SCRIPT" ]; then
  echo "error: missing $COMPACT_SCRIPT" >&2
  exit 1
fi

CONTRACT_SIDECAR_SCRIPT="$ROOT_DIR/scripts/wasm/generate-bootstrap-l0-contract-sidecar.mjs"
if [ ! -f "$CONTRACT_SIDECAR_SCRIPT" ]; then
  echo "error: missing $CONTRACT_SIDECAR_SCRIPT" >&2
  exit 1
fi
CONTRACT_SIDECAR_OUT="$ROOT_DIR/doc/wasm/bootstrap-l0-contract.v1.json"

STARTUP_SYMBOL_SCOPE_SCRIPT="$ROOT_DIR/scripts/wasm/collect-startup-symbol-scope.lisp"
if [ ! -f "$STARTUP_SYMBOL_SCOPE_SCRIPT" ]; then
  echo "error: missing $STARTUP_SYMBOL_SCOPE_SCRIPT" >&2
  exit 1
fi
STARTUP_SYMBOL_SCOPE_OUT="$ROOT_DIR/doc/wasm/startup-symbol-scope.source_scope_v1.json"

SCRIPT_ARGS=()
if [ "$FORCE" -eq 1 ]; then
  SCRIPT_ARGS+=(--force)
fi
if [ "$TRACE" -eq 1 ]; then
  SCRIPT_ARGS+=(--trace-modules)
fi

INLINE_TMP=""
if [ -n "$MODULES_OUT" ]; then
  INLINE_TMP="${MODULES_OUT}.inline-v1.tmp.json"
  SCRIPT_ARGS+=(--modules-out "$INLINE_TMP")
fi
if [ -n "$MODULES_DEBUG_OUT" ]; then
  SCRIPT_ARGS+=(--modules-debug-out "$MODULES_DEBUG_OUT")
fi

# Bundled module outputs require a complete recompilation pass so every module
# contributes to %wasm-compiled-modules% in this process.
if [ -n "$MODULES_OUT" ] || [ -n "$MODULES_DEBUG_OUT" ]; then
  FORCE=1
fi

if [ "$FORCE" -eq 1 ] && [[ ! " ${SCRIPT_ARGS[*]} " =~ " --force " ]]; then
  SCRIPT_ARGS+=(--force)
fi
if [ "${#SCRIPT_ARGS[@]}" -gt 0 ]; then
  run "$CCL_BIN" --no-init --batch -l "$SCRIPT" -- "${SCRIPT_ARGS[@]}"
else
  run "$CCL_BIN" --no-init --batch -l "$SCRIPT"
fi

run node "$CONTRACT_SIDECAR_SCRIPT" --out "$CONTRACT_SIDECAR_OUT"
run "$CCL_BIN" --no-init --batch -l "$STARTUP_SYMBOL_SCOPE_SCRIPT" -- \
  --repo-root "$ROOT_DIR" \
  --out "$STARTUP_SYMBOL_SCOPE_OUT" \
  --feature-profile wasm32-target-v1 \
  --contract-json "$CONTRACT_SIDECAR_OUT"

if [ -n "$MODULES_OUT" ]; then
  if [ "$DRYRUN" -eq 1 ]; then
    printf '+ node --input-type=module <attach-startup-binding-map-inline> %q %q %q\n' \
      "$ROOT_DIR" "$INLINE_TMP" "$STARTUP_SYMBOL_SCOPE_OUT"
  else
    node --input-type=module - "$ROOT_DIR" "$INLINE_TMP" "$STARTUP_SYMBOL_SCOPE_OUT" <<'NODE'
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [rootDir, inlineManifestPath, scopePath] = process.argv.slice(2);
const startupBindingMapModule = await import(
  pathToFileURL(path.join(rootDir, "doc/wasm/js/startup-binding-map.mjs")).href,
);
const {
  buildStartupBindingMapArtifact,
  summarizeStartupBindingMapArtifact,
} = startupBindingMapModule;

const [inlineManifestRaw, scopeRaw] = await Promise.all([
  fs.readFile(inlineManifestPath, "utf8"),
  fs.readFile(scopePath, "utf8"),
]);
const inlineManifest = JSON.parse(inlineManifestRaw);
const scopeArtifact = JSON.parse(scopeRaw);

const startupBindingMap = await buildStartupBindingMapArtifact({
  repoRoot: rootDir,
  functions: Array.isArray(inlineManifest?.functions) ? inlineManifest.functions : [],
  scopeArtifact,
  resolutionArtifact: null,
});
inlineManifest.startupBindingMap = startupBindingMap;
await fs.writeFile(inlineManifestPath, `${JSON.stringify(inlineManifest)}\n`, "utf8");

const counts = summarizeStartupBindingMapArtifact(startupBindingMap);
console.log(
  "startup binding map attached to inline manifest:" +
  ` total=${counts.total_entries}` +
  ` literal=${counts.literal_entries}` +
  ` entry-backed=${counts.entry_backed_entries}` +
  ` deferred=${counts.deferred_entries}` +
  ` unsupported=${counts.unsupported_entries}`,
);
NODE
  fi
  run node "$PACK_SCRIPT" --manifest "$INLINE_TMP" --out-manifest "$MODULES_OUT"
  if [ "$COMPACT_RUNTIME_MODULES" -eq 1 ]; then
    COMPACT_ARGS=(
      --manifest "$MODULES_OUT"
      --in-place
      --const-pool-shared-blob
      --const-pool-shared-blob-encoding br
      --brotli-quality 7
    )
    if [ "$STRIP_RUNTIME_FUNCTIONS" -eq 1 ]; then
      COMPACT_ARGS+=(--strip-functions)
    fi
    run node "$COMPACT_SCRIPT" "${COMPACT_ARGS[@]}"
  fi
  if [ "$DRYRUN" -eq 0 ]; then
    INLINE_TMP_BIN="${INLINE_TMP%.*}.bin"
    INLINE_TMP_IDX="${INLINE_TMP%.*}.idx"
    rm -f "$INLINE_TMP" "$INLINE_TMP_BIN" "$INLINE_TMP_IDX"
  fi
fi
