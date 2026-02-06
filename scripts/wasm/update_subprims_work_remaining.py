import bisect
import json
import re
from pathlib import Path

MAP_PATH = Path("doc/wasm/subprims-map.json")
PROVIDER_PATH = Path("lisp-kernel/wasm-subprims-provider.c")
KERNEL_STUB_PATH = Path("lisp-kernel/wasm-kernel-stubs.c")
PLAN_PATH = Path("doc/wasm/subprims-provider-plan.md")
OUT_PATH = Path("doc/wasm/subprims-work-remaining.md")


def load_symbols():
    return json.loads(MAP_PATH.read_text())["symbols"]


def build_line_index(text: str):
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def idx_to_line(starts, idx: int) -> int:
    return bisect.bisect_right(starts, idx)


COMMENT_RE = re.compile(r"/\*.*?\*/|//.*?$", re.S | re.M)


def strip_comments(s: str) -> str:
    return re.sub(COMMENT_RE, "", s)


def extract_body_range(text: str, name: str):
    m = re.search(r"\b" + re.escape(name) + r"\s*\([^;]*?\)\s*\{", text)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                return (start, end)
        i += 1
    return None


def find_condition(body_lines, trap_idx):
    if body_lines[trap_idx].strip().startswith("default:"):
        return ("default:", trap_idx)
    if trap_idx > 0 and body_lines[trap_idx - 1].strip().startswith("default:"):
        return ("default:", trap_idx - 1)

    j = trap_idx
    while j >= 0:
        line = body_lines[j].strip()
        if line.startswith("if ") or line.startswith("if(") or line.startswith("else if") or line.startswith("else if("):
            cond_line = line
            if "(" in cond_line and ")" not in cond_line:
                k = j + 1
                while k < len(body_lines):
                    cond_line += " " + body_lines[k].strip()
                    if ")" in body_lines[k]:
                        break
                    k += 1
            m = re.search(r"if\s*\((.*)\)", cond_line)
            if m:
                return (m.group(1), j)
            return (cond_line, j)
        if line.startswith("default:"):
            return ("default:", j)
        j -= 1
    return (None, None)


def classify_condition(cond):
    tags = set()
    if cond is None:
        tags.add("unconditional")
        return tags
    if cond == "default:":
        tags.add("unsupported-case")
        return tags

    c = cond

    if "tcr" in c and "NULL" in c:
        tags.add("tcr-null")
    if "NULL" in c or "nil_value" in c or re.search(r"==\s*0\b", c):
        tags.add("null/invalid")
    if any(tok in c for tok in ["tag_of", "fulltag_of", "header_subtag", "nodeheader_tag_p", "subtag"]):
        tags.add("type/subtag")
    if "fixnum" in c or "tag_fixnum" in c:
        tags.add("fixnum")
    if re.search(r"[<>]=?|!=", c) and any(tok in c for tok in ["index", "count", "len", "limit", "argc", "nargs", "offset", "slot", "size", "bits", "pos", "shift"]):
        tags.add("bounds")
    if "alloc" in c or "misc_alloc" in c:
        tags.add("alloc")
    if any(tok in c for tok in ["catch", "unwind", "db_link", "tlb", "vsp", "tsp", "nfp", "frame", "xframe", "pending_throw", "unwinding"]):
        tags.add("state/unwind")
    if not tags:
        tags.add("unknown")
    return tags


def parse_tier_map():
    tier_map = {}
    plan_text = PLAN_PATH.read_text()
    current_tier = None
    for line in plan_text.splitlines():
        if line.startswith("### Tier 0"):
            current_tier = "0"
            continue
        if line.startswith("### Tier 1"):
            current_tier = "1"
            continue
        if line.startswith("### ") and not line.startswith("### Tier"):
            current_tier = None
            continue
        if current_tier:
            m = re.search(r"`(_SP[^`]+)`", line)
            if m:
                tier_map[m.group(1)] = current_tier
    return tier_map


def main():
    symbols = load_symbols()
    provider_text = PROVIDER_PATH.read_text()
    provider_lines = provider_text.splitlines()
    line_starts = build_line_index(provider_text)

    export_names = re.findall(r"export_name\(\"(_SP[^\"]+)\"\)", provider_text)
    export_set = set(export_names)

    kernel_text = KERNEL_STUB_PATH.read_text()
    kernel_exports = set(re.findall(r"export_name\(\"(_SP[^\"]+)\"\)", kernel_text))

    tier_map = parse_tier_map()

    func_name_pattern = re.compile(r"\n[^\n]*\n([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\n\{")
    func_names = func_name_pattern.findall(provider_text)

    helper_trap_funcs = set()
    helper_trap_info = {}

    for name in func_names:
        if name in export_set:
            continue
        body_range = extract_body_range(provider_text, name)
        if not body_range:
            continue
        body_start, body_end = body_range
        body_text = provider_text[body_start + 1 : body_end]
        body_nc = strip_comments(body_text)
        if "wasm_subprims_trap()" not in body_nc:
            continue
        helper_trap_funcs.add(name)

        trap_sites = []
        body_lines = body_text.splitlines()
        body_start_line = idx_to_line(line_starts, body_start + 1)
        for m in re.finditer(r"wasm_subprims_trap\(\)", body_text):
            trap_idx = m.start()
            trap_line = idx_to_line(line_starts, body_start + 1 + trap_idx)
            line_idx = trap_line - body_start_line
            if line_idx < 0 or line_idx >= len(body_lines):
                line_idx = max(0, min(len(body_lines) - 1, line_idx))
            cond, cond_idx = find_condition(body_lines, line_idx)
            cond_line = body_start_line + cond_idx if cond_idx is not None else None
            tags = sorted(classify_condition(cond))
            trap_sites.append(
                {
                    "trap_line": trap_line,
                    "cond_line": cond_line,
                    "cond": cond if cond is not None else "<unconditional>",
                    "tags": tags,
                }
            )
        helper_tags = sorted(set(tag for t in trap_sites for tag in t["tags"]))
        helper_trap_info[name] = {
            "trap_sites": trap_sites,
            "tags": helper_tags,
            "trap_count": len(trap_sites),
        }

    validation_tag_set = {"tcr-null", "null/invalid", "type/subtag", "fixnum", "bounds", "alloc"}
    gap_tag_set = {"state/unwind", "unsupported-case", "unconditional", "unknown"}

    rows = []
    trap_detail_rows = []
    summary = {"stub": 0, "guarded": 0, "indirect": 0, "clean": 0, "missing": 0}

    def helper_condition_snippets(helper):
        info = helper_trap_info.get(helper)
        if not info:
            return []
        conds = []
        seen = set()
        for site in info["trap_sites"]:
            c = site["cond"]
            if c not in seen:
                seen.add(c)
                conds.append(c)
        return conds

    for name in symbols:
        body_range = extract_body_range(provider_text, name)
        if body_range is None:
            status = "missing"
            direct_trap_count = 0
            direct_tags = set()
            helper_calls = []
            helper_tags = set()
            trap_sites = []
            helper_cond_snips = []
            unknown_conditions = []
        else:
            body_start, body_end = body_range
            body_text = provider_text[body_start + 1 : body_end]
            body_nc = strip_comments(body_text)
            direct_trap_count = len(re.findall(r"wasm_subprims_trap\(\)", body_nc))
            body_compact = re.sub(r"\s+", "", body_nc)
            if re.fullmatch(r"wasm_subprims_trap\(\);(?:return;)?", body_compact):
                status = "stub"
            elif direct_trap_count > 0:
                status = "guarded"
            else:
                status = "clean"

            trap_sites = []
            direct_tags = set()
            unknown_conditions = []
            body_lines = body_text.splitlines()
            body_start_line = idx_to_line(line_starts, body_start + 1)
            for m in re.finditer(r"wasm_subprims_trap\(\)", body_text):
                trap_idx = m.start()
                trap_line = idx_to_line(line_starts, body_start + 1 + trap_idx)
                line_idx = trap_line - body_start_line
                if line_idx < 0 or line_idx >= len(body_lines):
                    line_idx = max(0, min(len(body_lines) - 1, line_idx))
                cond, cond_idx = find_condition(body_lines, line_idx)
                cond_line = body_start_line + cond_idx if cond_idx is not None else None
                tags = classify_condition(cond)
                direct_tags.update(tags)
                if "unknown" in tags:
                    unknown_conditions.append(cond if cond is not None else "<unconditional>")
                trap_sites.append(
                    {
                        "trap_line": trap_line,
                        "cond_line": cond_line,
                        "cond": cond if cond is not None else "<unconditional>",
                        "tags": sorted(tags),
                    }
                )

            helper_calls = []
            helper_tags = set()
            helper_cond_snips = []
            for helper in sorted(helper_trap_funcs):
                if re.search(r"\b" + re.escape(helper) + r"\s*\(", body_nc):
                    helper_calls.append(helper)
                    helper_tags.update(helper_trap_info.get(helper, {}).get("tags", []))
                    for c in helper_condition_snippets(helper):
                        helper_cond_snips.append(f"{helper}: {c}")
                    for site in helper_trap_info.get(helper, {}).get("trap_sites", []):
                        if "unknown" in site.get("tags", []):
                            unknown_conditions.append(site.get("cond", "<unconditional>"))

            if status == "clean" and helper_calls:
                status = "indirect"

        summary[status] += 1

        all_tags = set(direct_tags) | set(helper_tags)
        validation_types = sorted(all_tags & validation_tag_set)
        gap_types = sorted(all_tags & gap_tag_set)

        if status in ("stub", "missing"):
            work_remaining = "unimplemented"
        elif gap_types:
            work_remaining = "behavioral gap"
        elif status in ("guarded", "indirect"):
            work_remaining = "validation only"
        else:
            work_remaining = "clean"

        unknown_conditions_unique = []
        seen_unknown = set()
        for c in unknown_conditions:
            if c not in seen_unknown:
                seen_unknown.add(c)
                unknown_conditions_unique.append(c)

        if status in ("stub", "missing"):
            confidence = "n/a (unimplemented)"
        elif unknown_conditions_unique:
            conds = "; ".join([f"`{c}`" for c in unknown_conditions_unique])
            confidence = f"low: unknown conds -> {conds}"
        elif any(tag in all_tags for tag in ["state/unwind", "unsupported-case", "unconditional"]):
            confidence = "medium"
        else:
            confidence = "high"

        helper_cond_text = " - ".join([f"`{c}`" for c in helper_cond_snips]) if helper_cond_snips else "-"

        rows.append(
            {
                "name": name,
                "status": status,
                "work_remaining": work_remaining,
                "direct_trap_count": direct_trap_count,
                "direct_tags": ", ".join(sorted(direct_tags)) if direct_tags else "-",
                "helper_calls": ", ".join(helper_calls) if helper_calls else "-",
                "helper_tags": ", ".join(sorted(helper_tags)) if helper_tags else "-",
                "helper_conditions": helper_cond_text,
                "gap_types": ", ".join(gap_types) if gap_types else "-",
                "validation_types": ", ".join(validation_types) if validation_types else "-",
                "tier": tier_map.get(name, "-"),
                "kernel_impl": "yes" if name in kernel_exports else "no",
                "confidence": confidence,
            }
        )

        for site in trap_sites:
            trap_detail_rows.append(
                {
                    "name": name,
                    "trap_line": site["trap_line"],
                    "cond_line": site["cond_line"] if site["cond_line"] is not None else "-",
                    "cond": site["cond"],
                    "tags": ", ".join(site["tags"]) if site["tags"] else "-",
                }
            )

    rows.sort(key=lambda r: r["name"])
    trap_detail_rows.sort(key=lambda r: (r["name"], r["trap_line"]))

    helper_detail_rows = []
    for helper, info in sorted(helper_trap_info.items()):
        for site in info["trap_sites"]:
            helper_detail_rows.append(
                {
                    "helper": helper,
                    "trap_line": site["trap_line"],
                    "cond_line": site["cond_line"] if site["cond_line"] is not None else "-",
                    "cond": site["cond"],
                    "tags": ", ".join(site["tags"]) if site["tags"] else "-",
                }
            )

    work_summary = {}
    for r in rows:
        work_summary[r["work_remaining"]] = work_summary.get(r["work_remaining"], 0) + 1

    out = []
    out.append("# WASM Subprims Work Remaining (Critical Detail)")
    out.append("")
    out.append("Auto-generated status map for WASM subprims based on:")
    out.append("")
    out.append("- `doc/wasm/subprims-map.json` (canonical symbol list)")
    out.append("- `lisp-kernel/wasm-subprims-provider.c` (provider implementations)")
    out.append("- `lisp-kernel/wasm-kernel-stubs.c` (kernel-implemented subprims)")
    out.append("")
    out.append("**Status meanings**")
    out.append("")
    out.append("- `stub`: provider body is only `wasm_subprims_trap()` (always traps).")
    out.append("- `guarded`: provider body contains at least one direct `wasm_subprims_trap()` call.")
    out.append("- `indirect`: no direct trap, but calls a helper that can trap.")
    out.append("- `clean`: no direct trap and no helper trap calls detected.")
    out.append("- `missing`: no provider definition found; stand-in stub will be used.")
    out.append("")
    out.append("**Work remaining (derived)**")
    out.append("")
    out.append("- `unimplemented`: stub or missing.")
    out.append("- `behavioral gap`: traps include state/unwind, unsupported-case, unconditional, or unknown.")
    out.append("- `validation only`: traps appear to be input validation (type/bounds/null/alloc).")
    out.append("- `clean`: no trap paths detected.")
    out.append("")
    out.append("**Summary**")
    out.append("")
    out.append(f"- Total subprims: {len(symbols)}")
    out.append(f"- Stub: {summary['stub']}")
    out.append(f"- Guarded: {summary['guarded']}")
    out.append(f"- Indirect: {summary['indirect']}")
    out.append(f"- Clean: {summary['clean']}")
    out.append(f"- Missing: {summary['missing']}")
    out.append("")
    for k in sorted(work_summary):
        out.append(f"- {k}: {work_summary[k]}")
    out.append("")
    out.append("**Tier markers**")
    out.append("")
    out.append("- `0`: Tier-0 per `doc/wasm/subprims-provider-plan.md`")
    out.append("- `1`: Tier-1 per `doc/wasm/subprims-provider-plan.md`")
    out.append("- `-`: not listed in the tier plan")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Overview")
    out.append("")
    out.append("| Subprim | Status | Work Remaining | Direct Trap Count | Direct Tags | Helper Trap Calls | Helper Tags | Helper Trap Conditions | Gap Types | Validation Types | Tier | Kernel Impl | Confidence |")
    out.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        out.append(
            f"| `{r['name']}` | {r['status']} | {r['work_remaining']} | {r['direct_trap_count']} | {r['direct_tags']} | {r['helper_calls']} | {r['helper_tags']} | {r['helper_conditions']} | {r['gap_types']} | {r['validation_types']} | {r['tier']} | {r['kernel_impl']} | {r['confidence']} |"
        )

    out.append("")
    out.append("---")
    out.append("")
    out.append("## Direct Trap Site Details")
    out.append("")
    out.append("| Subprim | Trap Line | Cond Line | Condition | Tags |")
    out.append("| --- | --- | --- | --- | --- |")
    for r in trap_detail_rows:
        out.append(f"| `{r['name']}` | {r['trap_line']} | {r['cond_line']} | `{r['cond']}` | {r['tags']} |")

    out.append("")
    out.append("---")
    out.append("")
    out.append("## Helper Trap Site Details")
    out.append("")
    out.append("| Helper | Trap Line | Cond Line | Condition | Tags |")
    out.append("| --- | --- | --- | --- | --- |")
    for r in helper_detail_rows:
        out.append(f"| `{r['helper']}` | {r['trap_line']} | {r['cond_line']} | `{r['cond']}` | {r['tags']} |")

    OUT_PATH.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
