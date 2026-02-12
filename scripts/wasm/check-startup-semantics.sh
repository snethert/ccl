#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STARTUP_FILE="lisp-kernel/wasm-kernel-stubs.c"
L0_PRED_FILE="level-0/l0-pred.lisp"

STARTUP_CRITICAL_FUNCTIONS=(
  "wasm_set_command_line_output_arg"
  "wasm_run_script_with_output"
  "wasm_const_pool_intern_symbol"
  "wasm_const_pool_install"
)

STARTUP_COUPLED_PATHS=(
  "lisp-kernel/wasm-kernel-stubs.c"
  "doc/wasm/js/load-image.mjs"
  "doc/wasm/js/microkernel.mjs"
  "doc/wasm/js/startup-gate.mjs"
)

COUPLING_FLOOR_DEFAULT_REF="9462beba"

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/check-startup-semantics.sh [BASE [HEAD]]

Checks startup semantic guardrails:
- No forbidden startup bypass patterns added to lisp-kernel/wasm-kernel-stubs.c
  - global hard-fail tokens (any startup hunk)
  - function-context tokens only inside startup-critical functions
- No reintroduction of the level-0 require-structure-type istruct workaround
- Commit-coupling rule (range mode): commits touching startup debug/kernel paths
  must not also touch level-0/level-1

Diff selection:
- No args: staged + unstaged changes vs HEAD
- BASE:    BASE..HEAD
- BASE HEAD: BASE..HEAD
USAGE
}

if [ "$#" -gt 2 ]; then
  usage >&2
  exit 2
fi

if ! git -C "$ROOT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: $ROOT_DIR is not a git repository" >&2
  exit 2
fi

FAILED=0
DIFF_STARTUP=""
DIFF_L0_PRED=""
MODE_LABEL=""
COUPLING_FLOOR_REF=""

extract_hunk_function() {
  local hunk_context="$1"
  local fn="<unknown>"
  if [[ "$hunk_context" =~ ([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*\( ]]; then
    fn="${BASH_REMATCH[1]}"
  fi
  printf '%s' "$fn"
}

is_startup_critical_function() {
  local fn="$1"
  local critical
  for critical in "${STARTUP_CRITICAL_FUNCTIONS[@]}"; do
    if [ "$critical" = "$fn" ]; then
      return 0
    fi
  done
  return 1
}

is_startup_coupled_path() {
  local path="$1"
  local candidate
  for candidate in "${STARTUP_COUPLED_PATHS[@]}"; do
    if [ "$candidate" = "$path" ]; then
      return 0
    fi
  done
  return 1
}

is_level_semantic_path() {
  local path="$1"
  case "$path" in
    level-0/*|level-1/*) return 0 ;;
    *) return 1 ;;
  esac
}

match_global_token() {
  local line="$1"
  if [[ "$line" =~ %intern ]]; then
    printf '%s' "%intern"
    return 0
  fi
  if [[ "$line" =~ %findsym ]]; then
    printf '%s' "%findsym"
    return 0
  fi
  if [[ "$line" =~ wasm_const_pool_make_symbol ]]; then
    printf '%s' "wasm_const_pool_make_symbol"
    return 0
  fi
  if [[ "$line" =~ wasm_const_pool_ensure_package ]]; then
    printf '%s' "wasm_const_pool_ensure_package"
    return 0
  fi
  if [[ "$line" =~ wasm_const_pool_register_package ]]; then
    printf '%s' "wasm_const_pool_register_package"
    return 0
  fi
  if [[ "$line" =~ wasm_log_const_pool_fallback ]]; then
    printf '%s' "wasm_log_const_pool_fallback"
    return 0
  fi
  if [[ "$line" =~ creating[[:space:]]symbol[[:space:]]fallback ]]; then
    printf '%s' "creating symbol fallback"
    return 0
  fi
  if [[ "$line" =~ creating[[:space:]]package[[:space:]]fallback ]]; then
    printf '%s' "creating package fallback"
    return 0
  fi
  if [[ "$line" =~ nrs_KEYWORD_PACKAGE\.vcell[[:space:]]*= ]]; then
    printf '%s' "nrs_KEYWORD_PACKAGE.vcell ="
    return 0
  fi
  return 1
}

match_context_token() {
  local line="$1"
  if [[ "$line" =~ wasm_find_symbol_named_bytes_scan[[:space:]]*\( ]]; then
    printf '%s' "wasm_find_symbol_named_bytes_scan("
    return 0
  fi
  if [[ "$line" =~ WASM_LOAD_ENTRY_INDEX ]]; then
    printf '%s' "WASM_LOAD_ENTRY_INDEX"
    return 0
  fi
  if [[ "$line" =~ make_header[[:space:]]*\([[:space:]]*subtag_function[[:space:]]*,[[:space:]]*2[[:space:]]*\) ]]; then
    printf '%s' "make_header(subtag_function, 2)"
    return 0
  fi
  return 1
}

report_startup_violation() {
  local category="$1"
  local token="$2"
  local function_name="$3"
  local line_no="$4"
  local added_line="$5"
  FAILED=1
  echo "FAIL: [$category] $MODE_LABEL $STARTUP_FILE:$line_no function=$function_name token=$token" >&2
  echo "      +$added_line" >&2
}

scan_startup_diff() {
  local diff_text="$1"
  local line=""
  local current_function="<unknown>"
  local new_line=0
  local token=""

  while IFS= read -r line; do
    if [[ "$line" =~ ^@@\ -[0-9]+(,[0-9]+)?\ \+([0-9]+)(,[0-9]+)?\ @@(.*)$ ]]; then
      new_line="${BASH_REMATCH[2]}"
      current_function="$(extract_hunk_function "${BASH_REMATCH[4]}")"
      continue
    fi

    if [[ "$line" == +* && "$line" != "+++"* ]]; then
      local added_line="${line#+}"
      token="$(match_global_token "$added_line" || true)"
      if [ -n "$token" ]; then
        report_startup_violation "global-hard-fail" "$token" "$current_function" "$new_line" "$added_line"
      fi

      if is_startup_critical_function "$current_function"; then
        token="$(match_context_token "$added_line" || true)"
        if [ -n "$token" ]; then
          report_startup_violation "startup-function-context" "$token" "$current_function" "$new_line" "$added_line"
        fi
      fi

      new_line=$((new_line + 1))
      continue
    fi

    if [[ "$line" == " "* ]]; then
      new_line=$((new_line + 1))
    fi
  done <<<"$diff_text"
}

scan_l0_pred_diff_regressions() {
  local diff_text="$1"
  local line=""
  local new_line=0

  while IFS= read -r line; do
    if [[ "$line" =~ ^@@\ -[0-9]+(,[0-9]+)?\ \+([0-9]+)(,[0-9]+)?\ @@ ]]; then
      new_line="${BASH_REMATCH[2]}"
      continue
    fi
    if [[ "$line" == +* && "$line" != "+++"* ]]; then
      local added_line="${line#+}"
      if [[ "$added_line" =~ istruct-typep[[:space:]]+token ]]; then
        FAILED=1
        echo "FAIL: [semantic-regression] $MODE_LABEL $L0_PRED_FILE:$new_line function=require-structure-type token=istruct-typep token" >&2
        echo "      +$added_line" >&2
      fi
      new_line=$((new_line + 1))
      continue
    fi
    if [[ "$line" == " "* ]]; then
      new_line=$((new_line + 1))
    fi
  done <<<"$diff_text"
}

assert_l0_pred_baseline() {
  local l0_path="$ROOT_DIR/$L0_PRED_FILE"
  if ! rg -n -F "(if (typep token 'class-cell)" "$l0_path" >/dev/null; then
    FAILED=1
    echo "FAIL: [semantic-baseline] missing require-structure-type typep path in $L0_PRED_FILE" >&2
  fi
  if rg -n "istruct-typep[[:space:]]+token" "$l0_path" >/dev/null; then
    FAILED=1
    echo "FAIL: [semantic-baseline] detected istruct-typep token workaround in $L0_PRED_FILE" >&2
  fi
}

check_local_level_strict_mode() {
  local changed_level="$1"
  if [ -n "$changed_level" ]; then
    FAILED=1
    echo "FAIL: [local-strict] staged/unstaged level-0/level-1 changes are not allowed during startup semantic checks" >&2
    while IFS= read -r path; do
      [ -n "$path" ] && echo "      semantic-path: $path" >&2
    done <<<"$changed_level"
  fi
}

resolve_coupling_floor_ref() {
  local head_ref="$1"
  local candidate="${WASM_STARTUP_COUPLING_FLOOR:-$COUPLING_FLOOR_DEFAULT_REF}"
  if git -C "$ROOT_DIR" cat-file -e "${candidate}^{commit}" >/dev/null 2>&1 &&
     git -C "$ROOT_DIR" merge-base --is-ancestor "$candidate" "$head_ref" >/dev/null 2>&1; then
    COUPLING_FLOOR_REF="$(git -C "$ROOT_DIR" rev-parse --short "$candidate")"
  fi
}

check_commit_coupling_range() {
  local range="$1"
  local commit=""
  while IFS= read -r commit; do
    [ -z "$commit" ] && continue
    if [ -n "$COUPLING_FLOOR_REF" ] &&
       ! git -C "$ROOT_DIR" merge-base --is-ancestor "$COUPLING_FLOOR_REF" "$commit" >/dev/null 2>&1; then
      continue
    fi

    local touches_startup=0
    local touches_level=0
    local startup_files=""
    local level_files=""
    local path=""

    while IFS= read -r path; do
      [ -z "$path" ] && continue
      if is_startup_coupled_path "$path"; then
        touches_startup=1
        if [ -n "$startup_files" ]; then
          startup_files+=$'\n'
        fi
        startup_files+="$path"
      fi
      if is_level_semantic_path "$path"; then
        touches_level=1
        if [ -n "$level_files" ]; then
          level_files+=$'\n'
        fi
        level_files+="$path"
      fi
    done < <(git -C "$ROOT_DIR" show --pretty=format: --name-only --diff-filter=ACMRTUXB "$commit")

    if [ "$touches_startup" -eq 1 ] && [ "$touches_level" -eq 1 ]; then
      FAILED=1
      echo "FAIL: [commit-coupling] $MODE_LABEL commit=$commit touches startup debug/kernel paths and semantic layers in one commit" >&2
      while IFS= read -r path; do
        [ -n "$path" ] && echo "      startup-path: $path" >&2
      done <<<"$startup_files"
      while IFS= read -r path; do
        [ -n "$path" ] && echo "      semantic-path: $path" >&2
      done <<<"$level_files"
    fi
  done < <(git -C "$ROOT_DIR" rev-list --reverse "$range")
}

if [ "$#" -eq 0 ]; then
  MODE_LABEL="local(staged+unstaged)"
  DIFF_STARTUP+="$(git -C "$ROOT_DIR" diff --no-color --unified=0 HEAD -- "$STARTUP_FILE")"
  DIFF_STARTUP+=$'\n'
  DIFF_STARTUP+="$(git -C "$ROOT_DIR" diff --cached --no-color --unified=0 HEAD -- "$STARTUP_FILE")"

  DIFF_L0_PRED+="$(git -C "$ROOT_DIR" diff --no-color --unified=0 HEAD -- "$L0_PRED_FILE")"
  DIFF_L0_PRED+=$'\n'
  DIFF_L0_PRED+="$(git -C "$ROOT_DIR" diff --cached --no-color --unified=0 HEAD -- "$L0_PRED_FILE")"

  CHANGED_LEVEL="$({
    git -C "$ROOT_DIR" diff --name-only HEAD -- level-0 level-1
    git -C "$ROOT_DIR" diff --cached --name-only HEAD -- level-0 level-1
  } | sort -u)"

  scan_startup_diff "$DIFF_STARTUP"
  scan_l0_pred_diff_regressions "$DIFF_L0_PRED"
  check_local_level_strict_mode "$CHANGED_LEVEL"
else
  BASE="$1"
  HEAD_REF="${2:-HEAD}"
  RANGE="${BASE}..${HEAD_REF}"
  MODE_LABEL="range($RANGE)"
  resolve_coupling_floor_ref "$HEAD_REF"

  DIFF_STARTUP="$(git -C "$ROOT_DIR" diff --no-color --unified=0 "$RANGE" -- "$STARTUP_FILE")"
  DIFF_L0_PRED="$(git -C "$ROOT_DIR" diff --no-color --unified=0 "$RANGE" -- "$L0_PRED_FILE")"

  scan_startup_diff "$DIFF_STARTUP"
  scan_l0_pred_diff_regressions "$DIFF_L0_PRED"
  check_commit_coupling_range "$RANGE"
fi

assert_l0_pred_baseline

if [ "$FAILED" -eq 1 ]; then
  exit 1
fi

echo "PASS: startup semantics guardrails satisfied"
