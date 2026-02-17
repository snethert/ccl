#!/usr/bin/env bash
# check-lisp-syntax.sh — Fast parenthesis/reader check for Lisp files using CCL
#
# Uses CCL's reader with *read-suppress* = T to verify all forms can be read
# without errors. This catches unmatched parentheses, unterminated strings,
# and other reader-level syntax errors WITHOUT needing packages or definitions.
#
# Usage:
#   scripts/wasm/check-lisp-syntax.sh file.lisp [file2.lisp ...]
#   scripts/wasm/check-lisp-syntax.sh --modified     # check git-modified .lisp files
#   scripts/wasm/check-lisp-syntax.sh --compiler      # check all WASM compiler files
#   scripts/wasm/check-lisp-syntax.sh --all           # check all project .lisp files
#
# Exit codes: 0 = all OK, 1 = syntax errors found, 2 = usage error

set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v ccl >/dev/null 2>&1; then
  echo "error: ccl is required" >&2
  exit 2
fi

usage() {
  cat <<'EOF'
Usage: check-lisp-syntax.sh [options] [file ...]

Options:
  --modified      Check .lisp files modified in git working tree
  --compiler      Check WASM compiler files (compiler/WASM/*.lisp)
  --level0        Check WASM level-0 files (level-0/WASM/*.lisp)
  --all           Check all .lisp files in project (slow)
  -h, --help      Show this help

Examples:
  check-lisp-syntax.sh compiler/WASM/wasm2.lisp
  check-lisp-syntax.sh --modified
  check-lisp-syntax.sh --compiler --level0
EOF
}

FILES=()

while [ "${1:-}" != "" ]; do
  case "$1" in
    --modified)
      while IFS= read -r f; do
        if [[ "$f" == *.lisp ]]; then
          FILES+=("$ROOT_DIR/$f")
        fi
      done < <(git -C "$ROOT_DIR" diff --name-only HEAD 2>/dev/null; git -C "$ROOT_DIR" diff --name-only --cached 2>/dev/null; git -C "$ROOT_DIR" ls-files --others --exclude-standard 2>/dev/null)
      ;;
    --compiler)
      while IFS= read -r f; do
        FILES+=("$f")
      done < <(find "$ROOT_DIR/compiler/WASM" -name '*.lisp' -type f 2>/dev/null | sort)
      ;;
    --level0)
      while IFS= read -r f; do
        FILES+=("$f")
      done < <(find "$ROOT_DIR/level-0/WASM" -name '*.lisp' -type f 2>/dev/null | sort)
      ;;
    --all)
      while IFS= read -r f; do
        FILES+=("$f")
      done < <(find "$ROOT_DIR" \( -path '*/build' -o -path '*/.git' \) -prune -o -name '*.lisp' -type f -print 2>/dev/null | sort)
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "error: unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      # Resolve relative paths
      if [[ "$1" = /* ]]; then
        FILES+=("$1")
      else
        FILES+=("$ROOT_DIR/$1")
      fi
      ;;
  esac
  shift
done

if [ ${#FILES[@]} -eq 0 ]; then
  echo "error: no files specified" >&2
  usage
  exit 2
fi

# Deduplicate
UNIQUE_FILES=($(printf '%s\n' "${FILES[@]}" | sort -u))

# We pass file paths via a temp file to avoid shell quoting issues
FILELIST=$(mktemp)
trap 'rm -f "$FILELIST"' EXIT
printf '%s\n' "${UNIQUE_FILES[@]}" > "$FILELIST"

ccl --batch --quiet --eval "
(let ((total-forms 0)
      (total-files 0)
      (errors 0)
      (root \"$ROOT_DIR/\"))
  (with-open-file (flist \"$FILELIST\")
    (loop for path = (read-line flist nil nil)
          while path
          do (handler-case
                 (with-open-file (s path :external-format :utf-8)
                   (let ((*read-suppress* t))
                     (loop for form = (read s nil :eof)
                           until (eq form :eof)
                           count t into n
                           finally (let ((short (if (and (> (length path) (length root))
                                                        (string= path root :end1 (length root)))
                                                    (subseq path (length root))
                                                    path)))
                                     (format t \"  OK  ~a (~d forms)~%\" short n)
                                     (incf total-forms n)
                                     (incf total-files)))))
               (error (e)
                 (let ((short (if (and (> (length path) (length root))
                                       (string= path root :end1 (length root)))
                                  (subseq path (length root))
                                  path)))
                   (format t \"  FAIL ~a~%        ~a~%\" short e)
                   (force-output)
                   (incf errors))))))
  (format t \"~%~d file~:p, ~d form~:p, ~d error~:p~%\" total-files total-forms errors)
  (when (plusp errors)
    (format t \"~%SYNTAX ERRORS FOUND~%\")
    (ccl:quit 1)))
" 2>/dev/null
