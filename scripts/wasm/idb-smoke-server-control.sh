#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

NODE_BIN="${NODE_BIN:-node}"
PORT="${PORT:-5173}"
PID_FILE="${PID_FILE:-/tmp/ccl-idb-smoke-server.pid}"
LOG_FILE="${LOG_FILE:-/tmp/ccl-idb-smoke-server.log}"

usage() {
  cat <<'EOF'
Usage: scripts/wasm/idb-smoke-server-control.sh <command>

Commands:
  start    Start the idb smoke HTTP server
  stop     Stop the idb smoke HTTP server
  restart  Restart the idb smoke HTTP server
  status   Print current status
  url      Print smoke page URL
  logs     Print recent server log lines
EOF
}

smoke_url() {
  echo "http://127.0.0.1:${PORT}/doc/wasm/js/idb-smoke.html"
}

pid_from_file() {
  if [[ -f "${PID_FILE}" ]]; then
    cat "${PID_FILE}"
    return 0
  fi
  return 1
}

is_running_pid() {
  local pid="$1"
  [[ -n "${pid}" ]] || return 1
  kill -0 "${pid}" >/dev/null 2>&1
}

start_server() {
  local existing
  existing="$(pid_from_file || true)"
  if [[ -n "${existing}" ]] && is_running_pid "${existing}"; then
    echo "idb-smoke server already running (pid ${existing})"
    smoke_url
    return 0
  fi

  mkdir -p "$(dirname "${PID_FILE}")" "$(dirname "${LOG_FILE}")"
  rm -f "${PID_FILE}"

  (
    cd "${ROOT_DIR}"
    CCL_HTTP_ROOT="${ROOT_DIR}" PORT="${PORT}" "${NODE_BIN}" scripts/wasm/idb-smoke-server.mjs >>"${LOG_FILE}" 2>&1
  ) &
  local pid=$!
  echo "${pid}" >"${PID_FILE}"

  sleep 0.2
  if ! is_running_pid "${pid}"; then
    echo "failed to start idb-smoke server"
    if [[ -f "${LOG_FILE}" ]]; then
      tail -n 40 "${LOG_FILE}" || true
    fi
    rm -f "${PID_FILE}"
    return 1
  fi

  echo "idb-smoke server started (pid ${pid})"
  smoke_url
}

stop_server() {
  local pid
  pid="$(pid_from_file || true)"
  if [[ -z "${pid}" ]]; then
    echo "idb-smoke server is not running"
    return 0
  fi
  if ! is_running_pid "${pid}"; then
    rm -f "${PID_FILE}"
    echo "removed stale pid file"
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  for _ in {1..25}; do
    if ! is_running_pid "${pid}"; then
      rm -f "${PID_FILE}"
      echo "idb-smoke server stopped"
      return 0
    fi
    sleep 0.1
  done

  kill -9 "${pid}" >/dev/null 2>&1 || true
  rm -f "${PID_FILE}"
  echo "idb-smoke server killed"
}

status_server() {
  local pid
  pid="$(pid_from_file || true)"
  if [[ -n "${pid}" ]] && is_running_pid "${pid}"; then
    echo "idb-smoke server running (pid ${pid})"
    smoke_url
    return 0
  fi
  echo "idb-smoke server not running"
  return 1
}

print_logs() {
  if [[ ! -f "${LOG_FILE}" ]]; then
    echo "no log file: ${LOG_FILE}"
    return 0
  fi
  tail -n 80 "${LOG_FILE}"
}

cmd="${1:-}"
case "${cmd}" in
start)
  start_server
  ;;
stop)
  stop_server
  ;;
restart)
  stop_server
  start_server
  ;;
status)
  status_server
  ;;
url)
  smoke_url
  ;;
logs)
  print_logs
  ;;
*)
  usage
  exit 2
  ;;
esac
