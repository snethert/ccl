#!/bin/bash
# Discover cold-load entries that hang in infinite WASM loops.
# When a stuck entry is found at index N, skips N through N+RANGE_SIZE
# to handle blocks of consecutive stuck functions efficiently.
#
# Output: build/wasm32/cold-load-skip.txt (one index per line)

set -euo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

TIMEOUT=${TIMEOUT:-8}     # seconds of log stall before declaring stuck
RANGE_SIZE=${RANGE_SIZE:-50}  # skip this many consecutive entries per stuck
MAX_ITER=${MAX_ITER:-60}
SKIP_FILE="build/wasm32/cold-load-skip.txt"
LOG="/tmp/fasl-test.log"

while [[ $# -gt 0 ]]; do
  case $1 in
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --range) RANGE_SIZE="$2"; shift 2 ;;
    --max-iter) MAX_ITER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "$(dirname "$SKIP_FILE")"
: > "$SKIP_FILE"

echo "=== Cold-load entry discovery ==="
echo "Stall timeout: ${TIMEOUT}s, Range: ${RANGE_SIZE}, Max iter: ${MAX_ITER}"

for ((iter=1; iter<=MAX_ITER; iter++)); do
  echo ""
  echo "--- Iteration $iter (skip=$(wc -l < "$SKIP_FILE" | tr -d ' ') entries) ---"
  : > "$LOG"

  node scripts/wasm/lib/make-real-image.mjs --boot-modules 2>"$LOG" &
  PID=$!

  # Monitor log for stalls
  LAST_SIZE=0
  STALL_COUNT=0
  COMPLETED=false

  for ((t=0; t<600; t++)); do
    sleep 1
    if ! kill -0 "$PID" 2>/dev/null; then
      wait "$PID" 2>/dev/null || true
      COMPLETED=true
      break
    fi
    CUR_SIZE=$(wc -c < "$LOG" 2>/dev/null || echo 0)
    if [[ "$CUR_SIZE" == "$LAST_SIZE" ]]; then
      STALL_COUNT=$((STALL_COUNT + 1))
    else
      STALL_COUNT=0
      LAST_SIZE=$CUR_SIZE
    fi
    if [[ $STALL_COUNT -ge $TIMEOUT ]]; then
      break
    fi
  done

  if $COMPLETED; then
    echo "Process completed!"
    grep '\[stage\].*pass\|fasload-summary\|FAIL:' "$LOG" | tail -10
    echo "Skip file: $(wc -l < "$SKIP_FILE" | tr -d ' ') entries"
    break
  fi

  # Extract stuck entry (CLRO idx=NNN is at start of line)
  STUCK=$(grep '^CLRO idx=' "$LOG" | tail -1 | sed 's/^CLRO idx=\([0-9]*\) .*/\1/')
  if [[ -z "$STUCK" ]]; then
    echo "No CLRO entries found. Aborting."
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
    break
  fi

  # Add range to skip file
  END=$((STUCK + RANGE_SIZE - 1))
  echo "Stuck at entry $STUCK → skipping $STUCK..$END"
  for ((i=STUCK; i<=END; i++)); do
    echo "$i" >> "$SKIP_FILE"
  done

  # Deduplicate
  sort -un "$SKIP_FILE" -o "$SKIP_FILE"

  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true

  TOTAL_PROCESSED=$(grep -c '^CLRO idx=' "$LOG" 2>/dev/null || echo 0)
  echo "Processed $TOTAL_PROCESSED entries this iteration"
done

echo ""
echo "=== Discovery complete ==="
echo "Skip file: $SKIP_FILE ($(wc -l < "$SKIP_FILE" | tr -d ' ') entries)"
# Show ranges
echo "Ranges:"
awk 'NR==1{start=$1; prev=$1; next}
     $1!=prev+1{printf "  %d-%d\n", start, prev; start=$1}
     {prev=$1}
     END{printf "  %d-%d\n", start, prev}' "$SKIP_FILE"
