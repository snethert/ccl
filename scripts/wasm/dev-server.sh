#!/usr/bin/env bash
#
# CCL WASM HTTPS Development Server
#
# Starts a local HTTPS server for browser testing. Uses mkcert for
# locally-trusted certificates (no browser warnings).
#
# Usage:
#   scripts/wasm/dev-server.sh [--port PORT] [--mvp2]
#
# Options:
#   --port PORT   Port to listen on (default: 8080)
#   --mvp2        Enable SharedArrayBuffer headers for MVP-2 testing
#
# Prerequisites:
#   - mkcert (brew install mkcert)
#   - http-server (npm install -g http-server, or use npx)

set -euo pipefail

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

# Default configuration
PORT=8080
MVP2_MODE=0

# Parse arguments
while [ $# -gt 0 ]; do
  case "$1" in
    --port)
      shift
      PORT="${1:-8080}"
      ;;
    --mvp2)
      MVP2_MODE=1
      ;;
    -h|--help)
      cat <<'EOF'
CCL WASM HTTPS Development Server

Usage:
  scripts/wasm/dev-server.sh [--port PORT] [--mvp2]

Options:
  --port PORT   Port to listen on (default: 8080)
  --mvp2        Enable SharedArrayBuffer headers for MVP-2 testing
  -h, --help    Show this help

Examples:
  # Start server on default port (8080)
  scripts/wasm/dev-server.sh

  # Use custom port
  scripts/wasm/dev-server.sh --port 3000

  # Enable MVP-2 mode (SharedArrayBuffer support)
  scripts/wasm/dev-server.sh --mvp2

Prerequisites:
  brew install mkcert
  mkcert -install
EOF
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      echo "Run with --help for usage information" >&2
      exit 1
      ;;
  esac
  shift
done

# Check for mkcert
if ! command -v mkcert >/dev/null 2>&1; then
  cat <<'EOF' >&2
Error: mkcert not found

Install mkcert to create locally-trusted HTTPS certificates:

  macOS:
    brew install mkcert
    mkcert -install

  Linux (Debian/Ubuntu):
    sudo apt install mkcert
    mkcert -install

  Linux (other):
    See https://github.com/FiloSottile/mkcert
EOF
  exit 1
fi

# Generate certificate if it doesn't exist
CERT_FILE="${REPO_ROOT}/localhost-cert.pem"
KEY_FILE="${REPO_ROOT}/localhost-key.pem"

if [ ! -f "${CERT_FILE}" ] || [ ! -f "${KEY_FILE}" ]; then
  echo "Generating locally-trusted HTTPS certificate..."
  mkcert -key-file "${KEY_FILE}" -cert-file "${CERT_FILE}" localhost 127.0.0.1 ::1
  echo "Certificate created: ${CERT_FILE}"
fi

# Build server command
SERVER_CMD=(npx http-server . -p "${PORT}" -S -C "${CERT_FILE}" -K "${KEY_FILE}")

if [ "${MVP2_MODE}" -eq 1 ]; then
  echo "Starting HTTPS dev server (MVP-2 mode: SharedArrayBuffer enabled)"
  echo "Server: https://localhost:${PORT}"
  echo ""
  echo "MVP-2 headers enabled:"
  echo "  Cross-Origin-Opener-Policy: same-origin"
  echo "  Cross-Origin-Embedder-Policy: require-corp"
  echo ""
  SERVER_CMD+=(
    --cors
    -o "Cross-Origin-Opener-Policy: same-origin"
    -o "Cross-Origin-Embedder-Policy: require-corp"
  )
else
  echo "Starting HTTPS dev server (MVP-1 mode)"
  echo "Server: https://localhost:${PORT}"
  echo ""
  echo "To enable SharedArrayBuffer (MVP-2), run with --mvp2"
  echo ""
fi

echo "Press Ctrl+C to stop"
echo ""

# Run server
exec "${SERVER_CMD[@]}"
