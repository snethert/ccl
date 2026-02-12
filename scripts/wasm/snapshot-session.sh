#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_PATH="$ROOT_DIR/doc/wasm/session-handoff.json"

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/snapshot-session.sh [--out PATH]

Capture an instant-reacclimation snapshot for ongoing WASM startup diagnosis.
USAGE
}

resolve_path() {
  local value="$1"
  if [[ "$value" = /* ]]; then
    printf '%s\n' "$value"
  else
    printf '%s\n' "$ROOT_DIR/$value"
  fi
}

while [ "${1:-}" != "" ]; do
  case "$1" in
    --out)
      if [ -z "${2:-}" ]; then
        echo "error: --out requires a path" >&2
        exit 1
      fi
      OUT_PATH="$(resolve_path "$2")"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if ! git -C "$ROOT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: $ROOT_DIR is not a git repository" >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "error: node is required" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT_PATH")"

HEAD_SHA="$(git -C "$ROOT_DIR" rev-parse HEAD)"
HEAD_SHORT="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
BRANCH="$(git -C "$ROOT_DIR" symbolic-ref --short -q HEAD || echo detached)"
DIRTY_RAW="$(git -C "$ROOT_DIR" status --short)"

shopt -s nullglob
candidates=(
  /tmp/make-real-image*.log
  /tmp/make-real-image*.out
  /tmp/startup-repro*.log
  /tmp/xfasload_trace_build*.log
  /tmp/*runtime*smoke*.log
  /tmp/*sab*.log
)
shopt -u nullglob

LATEST_LOG=""
if [ "${#candidates[@]}" -gt 0 ]; then
  LATEST_LOG="$(
    for f in "${candidates[@]}"; do
      [ -f "$f" ] || continue
      printf '%s\t%s\n' "$(stat -f '%m' "$f" 2>/dev/null || echo 0)" "$f"
    done | sort -rn | head -n 1 | cut -f2-
  )"
fi

LATEST_REPRO_MANIFEST="$(find "$ROOT_DIR/doc/wasm/repro" -type f -name 'startup-repro-run-manifest.json' -print 2>/dev/null \
  | while IFS= read -r path; do
      printf '%s\t%s\n' "$(stat -f '%m' "$path" 2>/dev/null || echo 0)" "$path"
    done | sort -rn | head -n 1 | cut -f2- || true)"

FAIL_LINE=""
SIGNATURE_LINES=""
if [ -n "$LATEST_LOG" ] && [ -f "$LATEST_LOG" ]; then
  if command -v rg >/dev/null 2>&1; then
    FAIL_LINE="$(rg -n 'FAIL:|Error:|returned -7|No compiled-Lisp command.result observed' "$LATEST_LOG" | tail -n 1 || true)"
    SIGNATURE_LINES="$(rg -n 'STARTUP_FUNCTION_DESIGNATOR_GATE|boundary_probe|wasm_fasload_path|call\.post|throw\.detected|pending_raw|runtimeModulesManifest|No compiled-Lisp command.result' "$LATEST_LOG" | tail -n 20 || true)"
  else
    FAIL_LINE="$(grep -nE 'FAIL:|Error:|returned -7|No compiled-Lisp command.result observed' "$LATEST_LOG" | tail -n 1 || true)"
    SIGNATURE_LINES="$(grep -nE 'STARTUP_FUNCTION_DESIGNATOR_GATE|boundary_probe|wasm_fasload_path|call\.post|throw\.detected|pending_raw|runtimeModulesManifest|No compiled-Lisp command.result' "$LATEST_LOG" | tail -n 20 || true)"
  fi
fi

BLOCKER="No known blocker captured yet"
NEXT_ACTIONS=$'Run the failing command once with tracing enabled\nCapture and inspect the latest log signature lines\nUpdate this snapshot immediately after each diagnostic run'

if printf '%s\n%s\n' "$FAIL_LINE" "$SIGNATURE_LINES" | grep -q 'wasm_fasload_path'; then
  BLOCKER='Headless root-image build blocked by %FASLOAD throw boundary (call.post -> pending_raw=0x4)'
  NEXT_ACTIONS=$'Run CCL_WASM_TRACE=1 CCL_WASM_RUN_BOUNDARY_PROBES=1 node doc/wasm/js/make-real-image.mjs\nInspect wasm.fasload.trace.v2 call.post and throw.detected records in latest log\nConfirm *FASL-API* and %FASLOAD symbol states before first required fasload'
elif printf '%s\n%s\n' "$FAIL_LINE" "$SIGNATURE_LINES" | grep -q 'runtimeModulesManifest'; then
  BLOCKER='Manifest hash gate mismatch blocks runtime diagnosis'
  NEXT_ACTIONS=$'Regenerate runtime modules and root image manifest via repro pipeline\nRun root-image-manifest-smoke and capture expected vs actual hash\nSnapshot session state'
elif printf '%s\n%s\n' "$FAIL_LINE" "$SIGNATURE_LINES" | grep -q 'No compiled-Lisp command.result observed'; then
  BLOCKER='SAB command egress missing compiled Lisp result'
  NEXT_ACTIONS=$'Run runtime-command-sab-smoke with trace enabled\nInspect runtime bridge pump and command dispatch traces\nSnapshot session state'
fi

TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

HEAD_SHA="$HEAD_SHA" \
HEAD_SHORT="$HEAD_SHORT" \
BRANCH="$BRANCH" \
DIRTY_RAW="$DIRTY_RAW" \
LATEST_LOG="$LATEST_LOG" \
LATEST_REPRO_MANIFEST="$LATEST_REPRO_MANIFEST" \
FAIL_LINE="$FAIL_LINE" \
SIGNATURE_LINES="$SIGNATURE_LINES" \
BLOCKER="$BLOCKER" \
NEXT_ACTIONS="$NEXT_ACTIONS" \
OUT_PATH="$OUT_PATH" \
ROOT_DIR="$ROOT_DIR" \
node - <<'NODE' > "$TMP_JSON"
const fs = require('node:fs');
const path = require('node:path');

const rootDir = process.env.ROOT_DIR;
const rel = (value) => {
  if (!value) return null;
  const abs = path.resolve(value);
  const relPath = path.relative(rootDir, abs);
  if (!relPath || relPath.startsWith('..')) return value;
  return relPath.split(path.sep).join('/');
};

const dirtyFiles = (process.env.DIRTY_RAW || '')
  .split(/\r?\n/)
  .map((line) => line.trimEnd())
  .filter(Boolean);
const signature = (process.env.SIGNATURE_LINES || '')
  .split(/\r?\n/)
  .map((line) => line.trimEnd())
  .filter(Boolean);
const nextActions = (process.env.NEXT_ACTIONS || '')
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean);

const payload = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  repo: {
    root: rootDir,
    head_sha: process.env.HEAD_SHA || null,
    head_short: process.env.HEAD_SHORT || null,
    branch: process.env.BRANCH || null,
    dirty: dirtyFiles.length > 0,
    dirty_files: dirtyFiles,
  },
  current_blocker: process.env.BLOCKER || 'unknown',
  failing_command: process.env.FAIL_LINE || null,
  failure_signature: signature,
  artifacts: {
    latest_log: rel(process.env.LATEST_LOG || ''),
    latest_repro_manifest: rel(process.env.LATEST_REPRO_MANIFEST || ''),
  },
  next_actions: nextActions,
};

process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
NODE

mv "$TMP_JSON" "$OUT_PATH"
printf 'Wrote %s\n' "${OUT_PATH#"$ROOT_DIR"/}"
