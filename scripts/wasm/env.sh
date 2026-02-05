#!/usr/bin/env bash
set -euo pipefail

brew_prefix="$(brew --prefix 2>/dev/null || true)"
prefixes=(
  "${brew_prefix}/opt"
  /usr/local/opt
  /opt/homebrew/opt
)

find_opt() {
  local name="$1"
  for p in "${prefixes[@]}"; do
    if [[ -d "${p}/${name}" ]]; then
      printf '%s\n' "${p}/${name}"
      return 0
    fi
  done
  return 1
}

llvm_path="$(find_opt llvm || true)"
lld_path="$(find_opt lld || true)"
wasi_path="$(find_opt wasi-libc || true)"

if [[ -z "${llvm_path}" || -z "${lld_path}" || -z "${wasi_path}" ]]; then
  cat <<'EOF' >&2
Missing Homebrew dependencies. Install:
  brew install llvm lld wasi-libc
EOF
  return 1
fi

export CC="${llvm_path}/bin/clang -D__wasi__ -isystem ${wasi_path}/share/wasi-sysroot/include/wasm32-wasi"
export WASM_LD="${lld_path}/bin/wasm-ld"
