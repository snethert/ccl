#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_PREFIX="/private/tmp/step90"
LOG_GLOB="/private/tmp/make-real-image.resume*.trace.log"
TRACE_PATH_MODE="raw"
declare -a EXPLICIT_LOGS=()

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/recompute-resume-closure-matrix.sh [options]

Recomputes startup closure artifacts from resume trace logs, diffs against canonical
references, and exits non-zero if any diff is non-empty.

Options:
  --output-prefix <path>  Prefix for generated artifacts (default: /private/tmp/step90)
  --logs-glob <glob>      Glob used when explicit logs are not provided
                          (default: /private/tmp/make-real-image.resume*.trace.log)
  --log <path>            Explicit trace log path (repeatable)
  --trace-path-mode <m>   Trace path output mode: raw|canonical_private_tmp
                          (default: raw)
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-prefix)
      OUTPUT_PREFIX="$2"
      shift 2
      ;;
    --logs-glob)
      LOG_GLOB="$2"
      shift 2
      ;;
    --log)
      EXPLICIT_LOGS+=("$2")
      shift 2
      ;;
    --trace-path-mode)
      TRACE_PATH_MODE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$TRACE_PATH_MODE" != "raw" && "$TRACE_PATH_MODE" != "canonical_private_tmp" ]]; then
  echo "error: invalid --trace-path-mode: $TRACE_PATH_MODE" >&2
  exit 2
fi

declare -a LOGS=()
if [[ ${#EXPLICIT_LOGS[@]} -gt 0 ]]; then
  for log_path in "${EXPLICIT_LOGS[@]}"; do
    if [[ ! -f "$log_path" ]]; then
      echo "error: trace log not found: $log_path" >&2
      exit 2
    fi
    LOGS+=("$log_path")
  done
else
  # shellcheck disable=SC2086
  matched=( $LOG_GLOB )
  for log_path in "${matched[@]}"; do
    if [[ -f "$log_path" ]]; then
      LOGS+=("$log_path")
    fi
  done
fi

if [[ ${#LOGS[@]} -eq 0 ]]; then
  echo "error: no trace logs matched" >&2
  exit 2
fi

IFS=$'\n' read -r -d '' -a LOGS_SORTED < <(printf '%s\n' "${LOGS[@]}" | sort -u && printf '\0')

SIG_OUT="${OUTPUT_PREFIX}.signatures.recomputed.csv"
MAP_OUT="${OUTPUT_PREFIX}.trace-source-line-map.recomputed.csv"
MATRIX_OUT="${OUTPUT_PREFIX}.canonical-closure-matrix.recomputed.csv"
VIOL_OUT="${OUTPUT_PREFIX}.canonical-closure-violations.recomputed.csv"
PROFILE_COUNTS_OUT="${OUTPUT_PREFIX}.profile-counts.recomputed.csv"
TRACE_PROFILES_OUT="${OUTPUT_PREFIX}.trace-profiles.recomputed.csv"

DIFF_SIG_OUT="${OUTPUT_PREFIX}.diff.signatures.txt"
DIFF_MAP_OUT="${OUTPUT_PREFIX}.diff.trace-map.txt"
DIFF_MATRIX_OUT="${OUTPUT_PREFIX}.diff.matrix.txt"
DIFF_VIOL_OUT="${OUTPUT_PREFIX}.diff.violations.txt"
DIFF_PROFILE_COUNTS_OUT="${OUTPUT_PREFIX}.diff.profile-counts.txt"
DIFF_TRACE_PROFILES_OUT="${OUTPUT_PREFIX}.diff.trace-profiles.txt"

CANON_SIG="/private/tmp/step78.signatures.all-resume.csv"
CANON_MAP="/private/tmp/step80.trace-source-line-map.fixed.csv"
CANON_MATRIX="/private/tmp/step81.canonical-closure-matrix.csv"
CANON_VIOL="/private/tmp/step81.canonical-closure-violations.csv"
CANON_PROFILE_COUNTS="/private/tmp/step82.profile-counts.csv"
CANON_TRACE_PROFILES="/private/tmp/step82.trace-profiles.csv"

for required in \
  "$CANON_SIG" \
  "$CANON_MAP" \
  "$CANON_MATRIX" \
  "$CANON_VIOL" \
  "$CANON_PROFILE_COUNTS" \
  "$CANON_TRACE_PROFILES"; do
  if [[ ! -f "$required" ]]; then
    echo "error: canonical reference missing: $required" >&2
    exit 2
  fi
done

printf 'trace,apply_continue_count,boundary_count,prefasload_fail_count,fasload_fail_count,apply_payload_count,line_coupled_count,apply_flag,boundary_flag,prefasload_fail_flag,fasload_fail_flag,apply_payload_flag,line_coupled_flag\n' > "$SIG_OUT"
printf 'trace,apply_continue_line,boundary_lines,apply_payload_lines,line_coupled_lines,prefasload_fail_line,fasload_fail_line,source_emitter_window\n' > "$MAP_OUT"

tmpdir="$(mktemp -d /tmp/recompute-resume-closure-matrix.XXXXXX)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

for trace in "${LOGS_SORTED[@]}"; do
  base="$(basename "$trace")"
  trace_out="$trace"
  if [[ "$TRACE_PATH_MODE" == "canonical_private_tmp" ]]; then
    trace_out="/private/tmp/$base"
  fi
  ac_file="$tmpdir/${base}.ac.txt"
  b_file="$tmpdir/${base}.b.txt"
  pf_file="$tmpdir/${base}.pf.txt"
  wf_file="$tmpdir/${base}.wf.txt"
  ap_file="$tmpdir/${base}.ap.txt"

  # Guardrail: single-file lookups use rg -H -n.
  rg -H -n 'STARTUP_BINDING_MAP_APPLY_CONTINUE' "$trace" > "$ac_file" || true
  rg -H -n 'REQUIRED_FASLOAD_BOUNDARY' "$trace" > "$b_file" || true
  rg -H -n 'FAIL: pre-fasload startup binding map apply failed' "$trace" > "$pf_file" || true
  rg -H -n 'FAIL: wasm_fasload_path\(' "$trace" > "$wf_file" || true
  rg -H -n -F '"apply":{"schema_version":"startup_binding_map_apply_v1","status":"fail","phase":"pre-fasload"' "$trace" > "$ap_file" || true

  ac_count="$(awk 'END {print FNR+0}' "$ac_file")"
  b_count="$(awk 'END {print FNR+0}' "$b_file")"
  pf_count="$(awk 'END {print FNR+0}' "$pf_file")"
  wf_count="$(awk 'END {print FNR+0}' "$wf_file")"
  ap_count="$(awk 'END {print FNR+0}' "$ap_file")"

  ac_line="$(awk -F: 'FNR==1 {print $2; exit}' "$ac_file")"
  boundary_lines="$(awk -F: 'BEGIN{sep=""} {printf "%s%s", sep, $2; sep="|"}' "$b_file")"
  apply_payload_lines="$(awk -F: 'BEGIN{sep=""} {printf "%s%s", sep, $2; sep="|"}' "$ap_file")"
  pf_line="$(awk -F: 'FNR==1 {print $2; exit}' "$pf_file")"
  wf_line="$(awk -F: 'FNR==1 {print $2; exit}' "$wf_file")"

  b_nums="$tmpdir/${base}.b.lines"
  ap_nums="$tmpdir/${base}.ap.lines"
  awk -F: '{print $2}' "$b_file" > "$b_nums"
  awk -F: '{print $2}' "$ap_file" > "$ap_nums"

  line_coupled_lines="$(awk 'FNR==NR {seen[$1]=1; next} ($1 in seen) {if (!emit[$1]++) {printf "%s%s", sep, $1; sep="|"}}' "$b_nums" "$ap_nums")"
  line_coupled_count="$(awk 'FNR==NR {seen[$1]=1; next} ($1 in seen) {if (!emit[$1]++) count++} END {print count+0}' "$b_nums" "$ap_nums")"

  ac_flag="$((ac_count > 0 ? 1 : 0))"
  b_flag="$((b_count > 0 ? 1 : 0))"
  pf_flag="$((pf_count > 0 ? 1 : 0))"
  wf_flag="$((wf_count > 0 ? 1 : 0))"
  ap_flag="$((ap_count > 0 ? 1 : 0))"
  lc_flag="$((line_coupled_count > 0 ? 1 : 0))"

  source_window=""
  if [[ "$lc_flag" -eq 1 ]]; then
    source_window="doc/wasm/js/make-real-image.mjs:4938-4957"
  fi

  printf '%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n' \
    "$trace_out" "$ac_count" "$b_count" "$pf_count" "$wf_count" "$ap_count" "$line_coupled_count" \
    "$ac_flag" "$b_flag" "$pf_flag" "$wf_flag" "$ap_flag" "$lc_flag" >> "$SIG_OUT"

  printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$trace_out" "$ac_line" "$boundary_lines" "$apply_payload_lines" "$line_coupled_lines" "$pf_line" "$wf_line" "$source_window" >> "$MAP_OUT"
done

# Guardrail: FNR-safe per-file header handling for joins.
awk -F, '
  FNR==NR {
    if (FNR==1) {
      next
    }
    map_apply_line[$1]=$2
    map_boundary_lines[$1]=$3
    map_line_coupled_lines[$1]=$5
    map_prefasload_fail_line[$1]=$6
    map_fasload_fail_line[$1]=$7
    map_source_window[$1]=$8
    next
  }
  FNR==1 {
    print "trace,apply_flag,boundary_flag,apply_payload_flag,line_coupled_flag,prefasload_fail_flag,fasload_fail_flag,apply_continue_line,boundary_lines,line_coupled_lines,prefasload_fail_line,fasload_fail_line,source_linked_flag,positive_apply_closure_ok,nocontinue_prefasload_closure_ok,silent_baseline_profile"
    next
  }
  {
    trace=$1
    apply_flag=$8+0
    boundary_flag=$9+0
    prefasload_fail_flag=$10+0
    fasload_fail_flag=$11+0
    apply_payload_flag=$12+0
    line_coupled_flag=$13+0
    source_linked_flag=(length(map_source_window[trace])>0)?1:0

    if (apply_flag==1) {
      positive_apply_closure_ok=((boundary_flag==1 && apply_payload_flag==1 && line_coupled_flag==1 && prefasload_fail_flag==0)?1:0)
    } else {
      positive_apply_closure_ok=1
    }

    if (prefasload_fail_flag==1) {
      nocontinue_prefasload_closure_ok=((apply_flag==0 && boundary_flag==0 && apply_payload_flag==0 && line_coupled_flag==0)?1:0)
    } else {
      nocontinue_prefasload_closure_ok=1
    }

    silent_baseline_profile=((apply_flag==0 && boundary_flag==0 && apply_payload_flag==0 && line_coupled_flag==0 && prefasload_fail_flag==0 && fasload_fail_flag==0)?1:0)

    printf "%s,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s,%s,%d,%d,%d,%d\n", \
      trace, \
      apply_flag, \
      boundary_flag, \
      apply_payload_flag, \
      line_coupled_flag, \
      prefasload_fail_flag, \
      fasload_fail_flag, \
      map_apply_line[trace], \
      map_boundary_lines[trace], \
      map_line_coupled_lines[trace], \
      map_prefasload_fail_line[trace], \
      map_fasload_fail_line[trace], \
      source_linked_flag, \
      positive_apply_closure_ok, \
      nocontinue_prefasload_closure_ok, \
      silent_baseline_profile
  }
' "$MAP_OUT" "$SIG_OUT" > "$MATRIX_OUT"

awk -F, 'FNR==1 {next} (($14+0)==0 || ($15+0)==0 || ($1 ~ /make-real-image\.resume\.trace\.log$/ && ($16+0)!=1)) {print $1 ",closure_violation"}' "$MATRIX_OUT" > "$VIOL_OUT"

profile_counts_tmp="$tmpdir/profile-counts.tmp.csv"
awk -F, '
  FNR==1 {next}
  {
    k=$2 "," $3 "," $4 "," $5 "," $6 "," $7
    count[k]++
    traces[k]=(k in traces)?(traces[k] "|" $1):$1
  }
  END {
    print "apply_flag,boundary_flag,apply_payload_flag,line_coupled_flag,prefasload_fail_flag,fasload_fail_flag,count,traces"
    for (k in count) {
      print k "," count[k] "," traces[k]
    }
  }
' "$MATRIX_OUT" > "$profile_counts_tmp"

{
  head -n 1 "$profile_counts_tmp"
  tail -n +2 "$profile_counts_tmp" | sort -t, -k1,1n -k2,2n -k3,3n -k4,4n -k5,5n -k6,6n
} > "$PROFILE_COUNTS_OUT"

awk -F, '
  FNR==1 {next}
  {
    if ($2==1 && $3==1 && $4==1 && $5==1 && $6==0) {
      profile="applycontinue_boundary_payload_colocated"
    } else if ($2==0 && $3==0 && $6==1) {
      profile="nocontinue_prefasload_fail_no_boundary"
    } else if ($2==0 && $3==0 && $4==0 && $5==0 && $6==0 && $7==0) {
      profile="baseline_silent_no_attempt"
    } else {
      profile="other_profile"
    }
    print $1 "," profile
  }
' "$MATRIX_OUT" > "$TRACE_PROFILES_OUT"

diff -u "$CANON_SIG" "$SIG_OUT" > "$DIFF_SIG_OUT" || true
diff -u "$CANON_MAP" "$MAP_OUT" > "$DIFF_MAP_OUT" || true
diff -u "$CANON_MATRIX" "$MATRIX_OUT" > "$DIFF_MATRIX_OUT" || true
diff -u "$CANON_VIOL" "$VIOL_OUT" > "$DIFF_VIOL_OUT" || true
diff -u "$CANON_PROFILE_COUNTS" "$PROFILE_COUNTS_OUT" > "$DIFF_PROFILE_COUNTS_OUT" || true
diff -u "$CANON_TRACE_PROFILES" "$TRACE_PROFILES_OUT" > "$DIFF_TRACE_PROFILES_OUT" || true

status=0
for diff_file in \
  "$DIFF_SIG_OUT" \
  "$DIFF_MAP_OUT" \
  "$DIFF_MATRIX_OUT" \
  "$DIFF_VIOL_OUT" \
  "$DIFF_PROFILE_COUNTS_OUT" \
  "$DIFF_TRACE_PROFILES_OUT"; do
  wc -c "$diff_file"
  bytes="$(wc -c < "$diff_file")"
  if [[ "$bytes" -ne 0 ]]; then
    status=1
  fi
done

echo "artifact: $SIG_OUT"
echo "artifact: $MAP_OUT"
echo "artifact: $MATRIX_OUT"
echo "artifact: $VIOL_OUT"
echo "artifact: $PROFILE_COUNTS_OUT"
echo "artifact: $TRACE_PROFILES_OUT"
echo "artifact: $DIFF_SIG_OUT"
echo "artifact: $DIFF_MAP_OUT"
echo "artifact: $DIFF_MATRIX_OUT"
echo "artifact: $DIFF_VIOL_OUT"
echo "artifact: $DIFF_PROFILE_COUNTS_OUT"
echo "artifact: $DIFF_TRACE_PROFILES_OUT"

exit "$status"
