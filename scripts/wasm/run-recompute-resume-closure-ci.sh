#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

FIXTURE_DIR="${1:-doc/wasm/repro/fixtures/resume-trace-logs}"
WORK_DIR="${2:-/tmp/step97-fixtures}"
OUTPUT_PREFIX="${3:-/tmp/step97.ci}"

mkdir -p "$WORK_DIR"
rm -f "$WORK_DIR"/make-real-image.resume*.trace.log

shopt -s nullglob
fixture_files=( "$FIXTURE_DIR"/*.trace.log.gz )
shopt -u nullglob

if [[ ${#fixture_files[@]} -eq 0 ]]; then
  echo "error: no fixture files found under $FIXTURE_DIR" >&2
  exit 2
fi

for gz in "${fixture_files[@]}"; do
  out="$WORK_DIR/$(basename "${gz%.gz}")"
  gzip -cd "$gz" > "$out"
done

scripts/wasm/recompute-resume-closure-matrix.sh \
  --logs-glob "$WORK_DIR/make-real-image.resume*.trace.log" \
  --trace-path-mode canonical_private_tmp \
  --output-prefix "$OUTPUT_PREFIX"
