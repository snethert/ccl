#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC_DIR="${ROOT_DIR}/doc/wasm/spec"
CORE_DIR="${SPEC_DIR}/core-multipage"

CORE_URL="https://webassembly.github.io/spec/core/"

for cmd in wget; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: required command '$cmd' is not installed" >&2
    exit 1
  fi
done

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ccl-wasm-spec.XXXXXX")"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

CORE_STAGE="${TMP_DIR}/core-stage"
mkdir -p "$CORE_STAGE"

# Mirror the published multi-page core spec HTML tree.
wget \
  --quiet \
  --recursive \
  --no-parent \
  --page-requisites \
  --convert-links \
  --adjust-extension \
  --reject-regex '.*_download/WebAssembly\.pdf.*' \
  --execute robots=off \
  --directory-prefix "$CORE_STAGE" \
  "$CORE_URL"

mkdir -p "$SPEC_DIR"
rm -rf "$CORE_DIR"
mv "${CORE_STAGE}/webassembly.github.io/spec/core" "$CORE_DIR"

FETCHED_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
CORE_RELEASE_LINE="$(
  sed -n 's/.*\(Release [^<]*\).*/\1/p' "${CORE_DIR}/index.html" | head -n 1
)"
if [[ -z "$CORE_RELEASE_LINE" ]]; then
  CORE_RELEASE_LINE="unknown"
fi

cat > "${SPEC_DIR}/SOURCES.md" <<EOF
# WebAssembly Spec Sources

- Fetched (UTC): ${FETCHED_UTC}
- Core spec (multi-page HTML): ${CORE_URL}
- Core mirror entrypoint: doc/wasm/spec/core-multipage/index.html
- Core release string from mirror: ${CORE_RELEASE_LINE}
EOF

echo "Updated local WebAssembly spec mirror in ${SPEC_DIR}"
