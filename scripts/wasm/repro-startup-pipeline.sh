#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEFAULT_MANIFEST_REL="doc/wasm/root.image.manifest.json"
DEFAULT_RUN_ROOT_REL="doc/wasm/repro"
SESSION_HANDOFF_PATH="$ROOT_DIR/doc/wasm/session-handoff.json"

RUN_RUNTIME_DIAGNOSTICS=1
ALLOW_DIRTY_TREE=1
MANIFEST_PATH="$ROOT_DIR/$DEFAULT_MANIFEST_REL"
RUN_MANIFEST_PATH=""
MEMORY_FAILURE_SIGNATURE_PATTERN='WASM misc_alloc: reserve failed|wasm_memory_grow_and_relocate failed'

usage() {
  cat <<'EOF'
Usage: scripts/wasm/repro-startup-pipeline.sh [options]

Build a deterministic WASM startup artifact set from a clean build path,
capture provenance/artifact hashes, enforce manifest gate ordering, and emit
a machine-readable run manifest for triage.

Options:
  --manifest PATH            Root image manifest path (default: doc/wasm/root.image.manifest.json)
  --run-manifest-out PATH    Run manifest output path (default: doc/wasm/repro/<run-id>/startup-repro-run-manifest.json)
  --skip-runtime-diagnostics Skip post-gate runtime diagnosis smoke commands
  --require-clean-tree       Fail if git worktree is dirty before starting
  -h, --help                 Show this help
EOF
}

resolve_path() {
  local value="$1"
  if [[ "$value" = /* ]]; then
    printf '%s\n' "$value"
  else
    printf '%s\n' "$ROOT_DIR/$value"
  fi
}

to_repo_path() {
  local value="$1"
  if [[ "$value" == "$ROOT_DIR/"* ]]; then
    printf '%s\n' "${value#"$ROOT_DIR"/}"
  else
    printf '%s\n' "$value"
  fi
}

while [ "${1:-}" != "" ]; do
  case "$1" in
    --manifest)
      MANIFEST_PATH="$(resolve_path "${2:-}")"
      if [ -z "${2:-}" ]; then
        echo "error: --manifest requires a path" >&2
        exit 1
      fi
      shift
      ;;
    --run-manifest-out)
      RUN_MANIFEST_PATH="$(resolve_path "${2:-}")"
      if [ -z "${2:-}" ]; then
        echo "error: --run-manifest-out requires a path" >&2
        exit 1
      fi
      shift
      ;;
    --skip-runtime-diagnostics)
      RUN_RUNTIME_DIAGNOSTICS=0
      ;;
    --require-clean-tree)
      ALLOW_DIRTY_TREE=0
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

if ! command -v git >/dev/null 2>&1; then
  echo "error: git is required" >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "error: node is required" >&2
  exit 1
fi
if ! git -C "$ROOT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: $ROOT_DIR is not a git repository" >&2
  exit 1
fi

export TZ=UTC
export LC_ALL=C
export LANG=C

if { [ -z "${CC:-}" ] || [ -z "${WASM_LD:-}" ]; } && [ -f "$ROOT_DIR/scripts/wasm/env.sh" ]; then
  if ! . "$ROOT_DIR/scripts/wasm/env.sh" >/dev/null 2>&1; then
    echo "warning: scripts/wasm/env.sh could not be sourced; using existing CC/WASM_LD defaults" >&2
  fi
fi

if [ -n "${CCL_BIN:-}" ]; then
  RESOLVED_CCL_BIN="$CCL_BIN"
elif [ -x "$ROOT_DIR/dx86cl64" ]; then
  RESOLVED_CCL_BIN="$ROOT_DIR/dx86cl64"
elif command -v ccl >/dev/null 2>&1; then
  RESOLVED_CCL_BIN="ccl"
else
  echo "error: unable to resolve CCL binary (set CCL_BIN or install ccl)" >&2
  exit 1
fi
export CCL_BIN="$RESOLVED_CCL_BIN"

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

git_dirty_status() {
  if [ -n "$(git -C "$ROOT_DIR" status --porcelain)" ]; then
    printf '1\n'
  else
    printf '0\n'
  fi
}

version_line() {
  local command_text="${1:-}"
  local line=""
  if [ -n "$command_text" ]; then
    line="$(eval "$command_text --version 2>/dev/null | head -n 1" || true)"
  fi
  if [ -z "$line" ]; then
    line="unavailable"
  fi
  printf '%s\n' "$line"
}

GIT_SHA="$(git -C "$ROOT_DIR" rev-parse HEAD)"
GIT_SHORT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
GIT_BRANCH="$(git -C "$ROOT_DIR" symbolic-ref --short -q HEAD || echo detached)"
GIT_DIRTY_BEFORE="$(git_dirty_status)"

if [ "$ALLOW_DIRTY_TREE" -eq 0 ] && [ "$GIT_DIRTY_BEFORE" -ne 0 ]; then
  echo "error: worktree is dirty; rerun with a clean tree or omit --require-clean-tree" >&2
  exit 1
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$GIT_SHORT_SHA"
RUN_DIR="$ROOT_DIR/$DEFAULT_RUN_ROOT_REL/startup-pipeline-$RUN_ID"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"
STARTUP_SYMBOL_RESOLUTION_OUT="$RUN_DIR/startup-symbol-resolution.source_scope_v1.json"

if [ -z "$RUN_MANIFEST_PATH" ]; then
  RUN_MANIFEST_PATH="$RUN_DIR/startup-repro-run-manifest.json"
fi
mkdir -p "$(dirname "$RUN_MANIFEST_PATH")"

COMMAND_LOG_NDJSON="$RUN_DIR/commands.ndjson"
: > "$COMMAND_LOG_NDJSON"

PIPELINE_PROVENANCE_PATH="$RUN_DIR/build-provenance.json"

CC_COMMAND="${CC:-clang}"
WASM_LD_COMMAND="${WASM_LD:-wasm-ld-18}"
NODE_BIN="$(command -v node)"
CLANG_VERSION="$(version_line "$CC_COMMAND")"
WASM_LD_VERSION="$(version_line "$WASM_LD_COMMAND")"
CCL_VERSION="$(version_line "$CCL_BIN")"
NODE_VERSION="$(node --version 2>/dev/null || echo unavailable)"

node - "$PIPELINE_PROVENANCE_PATH" "$RUN_ID" "$GIT_SHA" "$GIT_SHORT_SHA" "$GIT_BRANCH" "$GIT_DIRTY_BEFORE" "$NODE_BIN" "$NODE_VERSION" "$CC_COMMAND" "$CLANG_VERSION" "$WASM_LD_COMMAND" "$WASM_LD_VERSION" "$CCL_BIN" "$CCL_VERSION" <<'NODE'
const fs = require("node:fs");
const [outPath, runId, gitSha, gitShort, gitBranch, gitDirtyBeforeRaw, nodeBin, nodeVersion, ccCommand, clangVersion, wasmLdCommand, wasmLdVersion, cclBin, cclVersion] = process.argv.slice(2);
const gitDirtyBefore = Number(gitDirtyBeforeRaw) !== 0;
const payload = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  source: "scripts/wasm/repro-startup-pipeline.sh",
  runId,
  git: {
    head: gitSha,
    short: gitShort,
    branch: gitBranch,
    dirtyBefore: gitDirtyBefore,
  },
  tools: {
    node: { command: nodeBin, version: nodeVersion },
    clang: { command: ccCommand, version: clangVersion },
    wasmLd: { command: wasmLdCommand, version: wasmLdVersion },
    ccl: { command: cclBin, version: cclVersion },
  },
  environment: {
    TZ: process.env.TZ ?? "",
    LC_ALL: process.env.LC_ALL ?? "",
    LANG: process.env.LANG ?? "",
  },
};
fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`);
NODE

MAKE_ARGS=()
if [ -n "${CC:-}" ]; then
  MAKE_ARGS+=("CC=$CC")
fi
if [ -n "${WASM_LD:-}" ]; then
  MAKE_ARGS+=("WASM_LD=$WASM_LD")
fi

RUNTIME_DIAG_COUNT=0
if [ "$RUN_RUNTIME_DIAGNOSTICS" -eq 1 ]; then
  RUNTIME_DIAG_COUNT=3
fi
TOTAL_STEPS=$((10 + RUNTIME_DIAG_COUNT))
STEP_INDEX=0
PIPELINE_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PIPELINE_STATUS="running"
FAILED_STEP=""
FAILED_EXIT_CODE=0
MANIFEST_GATE_STATUS="not-run"

snapshot_session_handoff() {
  if [ -x "$ROOT_DIR/scripts/wasm/snapshot-session.sh" ]; then
    "$ROOT_DIR/scripts/wasm/snapshot-session.sh" --out "$SESSION_HANDOFF_PATH" >/dev/null 2>&1 || true
  fi
}

trap snapshot_session_handoff EXIT

record_command_result() {
  local name="$1"
  local command_text="$2"
  local rc="$3"
  local started_at="$4"
  local finished_at="$5"
  local duration_seconds="$6"
  local log_path="$7"
  node - "$COMMAND_LOG_NDJSON" "$name" "$command_text" "$rc" "$started_at" "$finished_at" "$duration_seconds" "$log_path" <<'NODE'
const fs = require("node:fs");
const [outPath, name, commandText, rcRaw, startedAt, finishedAt, durationSecondsRaw, logPath] = process.argv.slice(2);
const rc = Number(rcRaw);
const row = {
  name,
  command: commandText,
  status: rc === 0 ? "pass" : "fail",
  exitCode: rc,
  startedAt,
  finishedAt,
  durationSeconds: Number(durationSecondsRaw),
  logPath,
};
fs.appendFileSync(outPath, `${JSON.stringify(row)}\n`);
NODE
}

run_step() {
  local name="$1"
  shift
  STEP_INDEX=$((STEP_INDEX + 1))
  local started_at finished_at started_seconds finished_seconds duration_seconds rc
  local step_slug="${name// /-}"
  local log_file="$LOG_DIR/$(printf '%02d' "$STEP_INDEX")-$step_slug.log"
  local log_repo_path
  log_repo_path="$(to_repo_path "$log_file")"
  local command_text
  printf -v command_text '%q ' "$@"
  command_text="${command_text% }"

  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  started_seconds="$(date +%s)"
  printf '[%s] STEP %d/%d %s\n' "$started_at" "$STEP_INDEX" "$TOTAL_STEPS" "$name"
  printf '+ %s\n' "$command_text"

  set +e
  (cd "$ROOT_DIR" && "$@") > >(tee "$log_file") 2>&1
  rc=$?
  set -e

  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  finished_seconds="$(date +%s)"
  duration_seconds=$((finished_seconds - started_seconds))

  record_command_result "$name" "$command_text" "$rc" "$started_at" "$finished_at" "$duration_seconds" "$log_repo_path"

  if [ "$rc" -ne 0 ]; then
    FAILED_STEP="$name"
    FAILED_EXIT_CODE="$rc"
    return "$rc"
  fi
  return 0
}

assert_no_memory_failure_signatures() {
  local matches=""
  matches="$(rg -n "$MEMORY_FAILURE_SIGNATURE_PATTERN" "$LOG_DIR" || true)"
  if [ -n "$matches" ]; then
    echo "error: detected memory failure signature in startup validation logs" >&2
    echo "$matches" >&2
    return 1
  fi
  return 0
}

write_run_manifest() {
  local final_status="$1"
  local finished_at="$2"
  local failure_step="${3:-}"
  local failure_code="${4:-0}"
  local git_dirty_after
  git_dirty_after="$(git_dirty_status)"
  node - "$RUN_MANIFEST_PATH" "$COMMAND_LOG_NDJSON" "$ROOT_DIR" "$RUN_ID" "$PIPELINE_STARTED_AT" "$finished_at" "$final_status" "$failure_step" "$failure_code" "$MANIFEST_GATE_STATUS" "$RUN_RUNTIME_DIAGNOSTICS" "$PIPELINE_PROVENANCE_PATH" "$MANIFEST_PATH" "$STARTUP_SYMBOL_SCOPE_OUT" "$GIT_SHA" "$GIT_SHORT_SHA" "$GIT_BRANCH" "$GIT_DIRTY_BEFORE" "$git_dirty_after" "$NODE_BIN" "$NODE_VERSION" "$CC_COMMAND" "$CLANG_VERSION" "$WASM_LD_COMMAND" "$WASM_LD_VERSION" "$CCL_BIN" "$CCL_VERSION" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const [
  outPath,
  commandsPath,
  repoRoot,
  runId,
  startedAt,
  finishedAt,
  finalStatus,
  failureStep,
  failureCodeRaw,
  manifestGateStatus,
  runtimeDiagnosticsRaw,
  provenancePath,
  rootManifestPath,
  startupSymbolScopePath,
  gitSha,
  gitShort,
  gitBranch,
  gitDirtyBeforeRaw,
  gitDirtyAfterRaw,
  nodeBin,
  nodeVersion,
  ccCommand,
  clangVersion,
  wasmLdCommand,
  wasmLdVersion,
  cclBin,
  cclVersion,
] = process.argv.slice(2);

const rel = (value) => {
  const abs = path.resolve(value);
  const relPath = path.relative(repoRoot, abs);
  return relPath.startsWith("..") ? abs : relPath.split(path.sep).join("/");
};

const readCommands = () => {
  if (!fs.existsSync(commandsPath)) return [];
  return fs.readFileSync(commandsPath, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
};

const sha256Hex = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");

const artifactPaths = [
  "doc/wasm/js/wasmcl.wasm",
  "doc/wasm/js/subprims.wasm",
  "doc/wasm/wasm-runtime-modules.json",
  "doc/wasm/wasm-runtime-modules.bin",
  "doc/wasm/wasm-runtime-modules.idx",
  "wasm-boot.image",
  "doc/wasm/root.image",
  rel(rootManifestPath),
  rel(startupSymbolScopePath),
];

const uniqueArtifactPaths = Array.from(new Set(artifactPaths));

const artifacts = uniqueArtifactPaths.map((repoPath) => {
  const abs = path.isAbsolute(repoPath)
    ? repoPath
    : path.resolve(repoRoot, repoPath);
  const displayPath = path.isAbsolute(repoPath) ? rel(repoPath) : repoPath;
  if (!fs.existsSync(abs)) {
    return {
      path: displayPath,
      exists: false,
      bytes: null,
      sha256: null,
    };
  }
  const bytes = fs.readFileSync(abs);
  return {
    path: displayPath,
    exists: true,
    bytes: bytes.length,
    sha256: sha256Hex(bytes),
  };
});

let provenanceDigest = null;
if (fs.existsSync(provenancePath)) {
  const bytes = fs.readFileSync(provenancePath);
  provenanceDigest = {
    path: rel(provenancePath),
    bytes: bytes.length,
    sha256: sha256Hex(bytes),
  };
}

const commands = readCommands();
const payload = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  source: "scripts/wasm/repro-startup-pipeline.sh",
  runId,
  status: finalStatus,
  startedAt,
  finishedAt,
  failure: finalStatus === "pass" ? null : {
    step: failureStep || null,
    exitCode: Number(failureCodeRaw) || 1,
  },
  gates: {
    manifestSmoke: manifestGateStatus,
    runtimeDiagnosticsRequested: Number(runtimeDiagnosticsRaw) === 1,
  },
  git: {
    head: gitSha,
    short: gitShort,
    branch: gitBranch,
    dirtyBefore: Number(gitDirtyBeforeRaw) === 1,
    dirtyAfter: Number(gitDirtyAfterRaw) === 1,
  },
  tools: {
    node: { command: nodeBin, version: nodeVersion },
    clang: { command: ccCommand, version: clangVersion },
    wasmLd: { command: wasmLdCommand, version: wasmLdVersion },
    ccl: { command: cclBin, version: cclVersion },
  },
  environment: {
    TZ: process.env.TZ ?? "",
    LC_ALL: process.env.LC_ALL ?? "",
    LANG: process.env.LANG ?? "",
  },
  files: {
    commandLog: rel(commandsPath),
    provenance: provenanceDigest,
  },
  commands,
  artifacts,
};

fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`);
NODE
}

echo "Run ID: $RUN_ID"
echo "Run directory: $(to_repo_path "$RUN_DIR")"
echo "Run manifest: $(to_repo_path "$RUN_MANIFEST_PATH")"
echo "Root manifest: $(to_repo_path "$MANIFEST_PATH")"
echo "Runtime diagnostics: $([ "$RUN_RUNTIME_DIAGNOSTICS" -eq 1 ] && echo enabled || echo skipped)"

if ! run_step "kernel-clean" make -C lisp-kernel/wasm32 "${MAKE_ARGS[@]}" clean; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "kernel-build" make -C lisp-kernel/wasm32 "${MAKE_ARGS[@]}"; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "subprims-clean" make -C lisp-kernel/wasm32/subprims "${MAKE_ARGS[@]}" clean; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "subprims-build" make -C lisp-kernel/wasm32/subprims "${MAKE_ARGS[@]}"; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "compile-runtime-modules" scripts/wasm/compile-wasm-fasls.sh --force --modules-out doc/wasm/wasm-runtime-modules.json; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "build-wasm-boot" scripts/wasm/build-wasm-boot.sh --force; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "generate-bootstrap-l0-contract-sidecar" node scripts/wasm/generate-bootstrap-l0-contract-sidecar.mjs --out "$(to_repo_path "$CONTRACT_SIDECAR_OUT")"; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "collect-startup-symbol-scope" "$CCL_BIN" --no-init --batch -l "$STARTUP_SYMBOL_SCOPE_SCRIPT" -- --repo-root "$(to_repo_path "$ROOT_DIR")" --out "$(to_repo_path "$STARTUP_SYMBOL_SCOPE_OUT")" --feature-profile wasm32-target-v1 --contract-json "$(to_repo_path "$CONTRACT_SIDECAR_OUT")"; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "make-root-image" node doc/wasm/js/make-real-image.mjs --output doc/wasm/root.image --manifest-out "$(to_repo_path "$MANIFEST_PATH")" --modules doc/wasm/wasm-runtime-modules.json --build-provenance "$(to_repo_path "$PIPELINE_PROVENANCE_PATH")" --startup-symbol-scope "$(to_repo_path "$STARTUP_SYMBOL_SCOPE_OUT")" --startup-symbol-resolution-out "$(to_repo_path "$STARTUP_SYMBOL_RESOLUTION_OUT")" --startup-symbol-contract "$(to_repo_path "$CONTRACT_SIDECAR_OUT")"; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="not-run"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
if ! run_step "manifest-smoke-gate" node doc/wasm/js/root-image-manifest-smoke.mjs --manifest "$(to_repo_path "$MANIFEST_PATH")"; then
  PIPELINE_STATUS="fail"
  MANIFEST_GATE_STATUS="fail"
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi
MANIFEST_GATE_STATUS="pass"

if [ "$RUN_RUNTIME_DIAGNOSTICS" -eq 1 ]; then
  if ! run_step "runtime-start-lisp-smoke" node doc/wasm/js/start-lisp-smoke.mjs; then
    PIPELINE_STATUS="fail"
    write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
    exit "$FAILED_EXIT_CODE"
  fi
  if ! run_step "runtime-command-smoke" node doc/wasm/js/runtime-command-smoke.mjs; then
    PIPELINE_STATUS="fail"
    write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
    exit "$FAILED_EXIT_CODE"
  fi
  if ! run_step "runtime-debugger-smoke" node doc/wasm/js/runtime-debugger-smoke.mjs; then
    PIPELINE_STATUS="fail"
    write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
    exit "$FAILED_EXIT_CODE"
  fi
fi

if ! assert_no_memory_failure_signatures; then
  PIPELINE_STATUS="fail"
  FAILED_STEP="memory-signature-assert"
  FAILED_EXIT_CODE=1
  write_run_manifest "$PIPELINE_STATUS" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FAILED_STEP" "$FAILED_EXIT_CODE"
  exit "$FAILED_EXIT_CODE"
fi

PIPELINE_STATUS="pass"
PIPELINE_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_run_manifest "$PIPELINE_STATUS" "$PIPELINE_FINISHED_AT"

echo "PASS: repro startup pipeline completed"
echo "Run manifest: $(to_repo_path "$RUN_MANIFEST_PATH")"
