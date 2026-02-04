#!/usr/bin/env python3
"""
Extract the ARM sptab order from lisp-kernel/arm-spentry.s and emit JSON.

The WASM backend uses fixnum indices whose ordering must match ARM's `sptab`,
so this file is the canonical source of truth for subprim index -> symbol name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    spentry = repo_root / "lisp-kernel" / "arm-spentry.s"
    text = spentry.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Find the `C(sptab):` block, then the following `local_label(start):`,
    # then capture all `.long <symbol>` entries until `local_label(end):`.
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
        # Ignore the label pointer word in the C(sptab) header.
        if sym.startswith("local_label("):
            continue
        symbols.append(sym)

    out = {
        "source": str(spentry.relative_to(repo_root)),
        "count": len(symbols),
        "symbols": symbols,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
