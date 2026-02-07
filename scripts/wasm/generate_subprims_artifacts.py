#!/usr/bin/env python3
"""Generate WASM subprims artifacts from the ARM sptab.

Source of truth: lisp-kernel/arm-spentry.s (C(sptab) local_label(start..end)).

Outputs:
- doc/wasm/subprims-map.json
- lisp-kernel/wasm-subprims-map.h
- lisp-kernel/wasm-subprims-standin.c

This keeps the WASM backend's table indices aligned with ARM, with
WASM-only stubs appended at the end.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def extract_symbols(spentry: Path) -> list[str]:
    text = spentry.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    sptab_idx = next((i for i, l in enumerate(lines) if re.search(r"\bC\(sptab\):", l)), None)
    if sptab_idx is None:
        raise SystemExit(f"Couldn't find C(sptab): in {spentry}")

    start_idx = next(
        (i for i in range(sptab_idx, len(lines)) if re.search(r"\blocal_label\(start\):", lines[i])),
        None,
    )
    if start_idx is None:
        raise SystemExit(f"Couldn't find local_label(start): after C(sptab): in {spentry}")

    end_idx = next(
        (i for i in range(start_idx + 1, len(lines)) if re.search(r"\blocal_label\(end\):", lines[i])),
        None,
    )
    if end_idx is None:
        raise SystemExit(f"Couldn't find local_label(end): after local_label(start): in {spentry}")

    sym_re = re.compile(r"^\s*\.long\s+([^\s/]+)")
    symbols: list[str] = []
    for line in lines[start_idx + 1 : end_idx]:
        m = sym_re.match(line)
        if not m:
            continue
        sym = m.group(1)
        if sym.startswith("local_label("):
            continue
        symbols.append(sym)

    return symbols


def write_json(repo_root: Path, symbols: list[str]) -> None:
    out = {
        "source": str((repo_root / "lisp-kernel" / "arm-spentry.s").relative_to(repo_root)),
        "count": len(symbols),
        "symbols": symbols,
    }
    path = repo_root / "doc" / "wasm" / "subprims-map.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_header(repo_root: Path, symbols: list[str]) -> None:
    path = repo_root / "lisp-kernel" / "wasm-subprims-map.h"
    lines: list[str] = []
    lines.append("/*")
    lines.append(" * Auto-generated from lisp-kernel/arm-spentry.s, with")
    lines.append(" * WASM-only stub entries appended at the end.")
    lines.append(" *")
    lines.append(" * Keep this in sync with the ARM sptab order; WASM subprim indices must match.")
    lines.append(" */")
    lines.append("")
    lines.append("#ifndef __ccl_wasm_subprims_map_h__")
    lines.append("#define __ccl_wasm_subprims_map_h__")
    lines.append("")
    lines.append(f"#define WASM_SUBPRIMS_COUNT {len(symbols)}")
    lines.append("")
    lines.append("#define FOR_EACH_WASM_SUBPRIM(X) \\")
    for i, sym in enumerate(symbols):
        tail = " \\" if i != len(symbols) - 1 else ""
        lines.append(f"  X({sym}){tail}")
    lines.append("")
    lines.append("#endif")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_standins(repo_root: Path, symbols: list[str]) -> None:
    exclude = {"_SPmakes32", "_SPfix_overflow", "_SPunused1", "_SPunused2"}
    path = repo_root / "lisp-kernel" / "wasm-subprims-standin.c"
    lines: list[str] = []
    lines.append("/*")
    lines.append(" * WASM subprims stand-ins (C)")
    lines.append(" *")
    lines.append(" * These are placeholders so the JS host can install a complete subprims table.")
    lines.append(" * Real implementations can later override table entries with handwritten WASM.")
    lines.append(" *")
    lines.append(" * NOTE: Some subprims are implemented in the kernel or smoke tests and")
    lines.append(" * are intentionally omitted here to avoid duplicate symbols.")
    lines.append(" */")
    lines.append("")
    lines.append("#ifdef WASM32")
    lines.append('#include "lisp.h"')
    lines.append('#include "lisp-exceptions.h"')
    lines.append('#include "wasm-subprims-map.h"')
    lines.append("")
    lines.append("#define DECL_SUBPRIM(name) \\")
    lines.append('  __attribute__((used, visibility("default"), export_name(#name))) void name(void)')
    lines.append("#define SUBPRIM_STUB(name) \\")
    lines.append('  DECL_SUBPRIM(name) { Bug(NULL, "WASM subprim not implemented: %s", #name); }')
    lines.append("")
    for sym in symbols:
        if sym in exclude:
            lines.append(f"/* {sym} provided elsewhere */")
            continue
        lines.append(f"SUBPRIM_STUB({sym})")
    lines.append("")
    lines.append("#undef SUBPRIM_STUB")
    lines.append("#undef DECL_SUBPRIM")
    lines.append("")
    lines.append("#endif")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    spentry = repo_root / "lisp-kernel" / "arm-spentry.s"

    symbols = extract_symbols(spentry)
    # WASM-only stubs (not part of the ARM sptab) appended after ARM entries.
    extras = ["_SPwasm_macro_apply_stub", "_SPwasm_udf_stub"]
    for sym in extras:
        if sym not in symbols:
            symbols.append(sym)
    write_json(repo_root, symbols)
    write_header(repo_root, symbols)
    write_standins(repo_root, symbols)

    print(f"Generated {len(symbols)} subprims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
