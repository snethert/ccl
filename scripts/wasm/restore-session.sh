#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_PATH="$ROOT_DIR/doc/wasm/session-handoff.json"

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/restore-session.sh [--in PATH] [--json]

Print an instant reacclimation summary from the session handoff snapshot.
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

PRINT_JSON=0
while [ "${1:-}" != "" ]; do
  case "$1" in
    --in)
      if [ -z "${2:-}" ]; then
        echo "error: --in requires a path" >&2
        exit 1
      fi
      INPUT_PATH="$(resolve_path "$2")"
      shift
      ;;
    --json)
      PRINT_JSON=1
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

if [ ! -f "$INPUT_PATH" ]; then
  echo "No handoff snapshot found at ${INPUT_PATH#"$ROOT_DIR"/}" >&2
  echo "Run: scripts/wasm/snapshot-session.sh" >&2
  exit 1
fi

if [ "$PRINT_JSON" -eq 1 ]; then
  cat "$INPUT_PATH"
  exit 0
fi

node - "$INPUT_PATH" <<'NODE'
const fs = require('node:fs');

const inputPath = process.argv[2];
const data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const repo = data.repo || {};
const artifacts = data.artifacts || {};
const dirtyFiles = Array.isArray(repo.dirty_files) ? repo.dirty_files : [];
const signature = Array.isArray(data.failure_signature) ? data.failure_signature : [];
const nextActions = Array.isArray(data.next_actions) ? data.next_actions : [];

console.log('Session Reacclimation');
console.log(`- generated_at: ${data.generated_at || 'unknown'}`);
console.log(`- head: ${repo.head_short || 'unknown'} (${repo.head_sha || 'unknown'}) branch=${repo.branch || 'unknown'}`);
console.log(`- dirty_tree: ${repo.dirty ? 'yes' : 'no'} (${dirtyFiles.length} files)`);
console.log(`- blocker: ${data.current_blocker || 'unknown'}`);
console.log(`- failing_command: ${data.failing_command || 'none captured'}`);
console.log(`- latest_log: ${artifacts.latest_log || 'none'}`);
console.log(`- latest_repro_manifest: ${artifacts.latest_repro_manifest || 'none'}`);

if (dirtyFiles.length) {
  console.log('Dirty Files');
  for (const line of dirtyFiles.slice(0, 12)) {
    console.log(`- ${line}`);
  }
  if (dirtyFiles.length > 12) {
    console.log(`- ... (${dirtyFiles.length - 12} more)`);
  }
}

if (signature.length) {
  console.log('Failure Signature');
  for (const line of signature.slice(-12)) {
    console.log(`- ${line}`);
  }
}

if (nextActions.length) {
  console.log('Next Actions');
  nextActions.forEach((line, idx) => {
    console.log(`${idx + 1}. ${line}`);
  });
}
NODE
