#!/usr/bin/env python3
"""Generate/check the documentation projections using only Python's standard library."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "outline.md": "Clozure_CL_WebAssembly_Port_Outline_v0_14.docx",
    "acceptance.md": "CCL_WebAssembly_Acceptance_Policy_and_Regression_Register_v1_4.docx",
    "decisions.md": "CCL_WebAssembly_Stage0_Desk_Decisions_v1_5.docx",
}
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
E.register_namespace("w", W)
E.register_namespace("r", R)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()


def stages(text):
    text = text.replace("Stages ", "").replace("Stage ", "")
    if text == "none":
        return []
    if text == "Gate 0":
        return ["Gate 0"]
    result = []
    for token in text.split(", "):
        if "–" in token:
            a, b = map(int, token.split("–"))
            result.extend(range(a, b + 1))
        else:
            result.append(int(token))
    return result


def obligations(source):
    records = []
    pattern = r"#### (LL\d\d)\s+/\s+([^\n]+)\n(.*?)(?=\n#### LL|\n### A\.|\n## 5|\Z)"
    for match in re.finditer(pattern, source, re.S):
        ident, title, body = match.groups()
        meta = re.search(r"First acceptance: ([^.]+)\. Extensions: ([^.]+)\.", body)
        if meta is None:
            raise ValueError(f"Missing stage metadata: {ident}")
        records.append({"id": ident, "title": title,
                        "first_acceptance": stages(meta[1]), "extensions": stages(meta[2]),
                        "standing_control": "Standing control." in body,
                        "regression": "all later stages in scope"})
    if [r["id"] for r in records] != [f"LL{i:02d}" for i in range(1, 25)]:
        raise ValueError("Expected exactly LL01–LL24 in the register")
    return records


def stage_ids(records, stage, field):
    return [r["id"] for r in records if not r["standing_control"] and stage in r[field]]


def projections():
    acceptance = (ROOT / "acceptance.md").read_text()
    records = obligations(acceptance)
    table = ["| Stage | First acceptance | Scheduled extensions |", "| --- | --- | --- |",
             "| Gate 0 | LL22: current U1 native baseline identity | Historical H1 acceptance retained separately. |"]
    for n in range(7):
        first = ", ".join(stage_ids(records, n, "first_acceptance")) or "None"
        ext = ", ".join(stage_ids(records, n, "extensions")) or "None"
        table.append(f"| Stage {n} | {first} | {ext} |")
    table.append("| Every stage | LL03, LL22, LL23, LL24 | Standing controls at Stages 0–6; LL22 also covers Gate 0. |")
    acceptance = re.sub(r"\| Stage \| First acceptance \| Scheduled extensions \|.*?(?=\n\n|\Z)",
                        "\n".join(table), acceptance, count=1, flags=re.S)
    outline = (ROOT / "outline.md").read_text()
    index = iter(range(7))

    def scheduled(_match):
        n = next(index)
        ids = sorted(set(stage_ids(records, n, "first_acceptance") + stage_ids(records, n, "extensions")))
        return "Scheduled LL tests: " + (", ".join(ids) + "." if ids else "no new stage-specific slice. All applicable continuing regressions remain mandatory.")

    outline, count = re.subn(r"^Scheduled LL tests:.*$", scheduled, outline, flags=re.M)
    if count != 7:
        raise ValueError("Expected seven outline stage lists")
    return {"acceptance.md": acceptance.encode(), "outline.md": outline.encode(),
            "stage0/obligations.json": json_bytes({"version": 1, "authority": "acceptance.md section 4",
                                                   "metadata": records})}


def node(parent, name, attrs=None, text=None):
    e = E.SubElement(parent, f"{{{W}}}{name}", {f"{{{W}}}{k}": str(v) for k, v in (attrs or {}).items()})
    if text is not None:
        e.text = text
    return e


def xml(element):
    return E.tostring(element, encoding="utf-8", xml_declaration=True)


def docx_bytes(markdown):
    import io
    doc = E.Element(f"{{{W}}}document")
    body = node(doc, "body")
    relationships = E.Element("Relationships", xmlns=PKG)
    E.SubElement(relationships, "Relationship", Id="rId1", Type=R + "/styles", Target="styles.xml")
    links = {}

    def runs(p, text, mono=False):
        # Supported source syntax: links, inline code and bold. Everything else is literal.
        parts = re.split(r"(\[[^\]]+\]\([^\s)]+\)|`[^`]+`|\*\*[^*]+\*\*)", text)
        for part in filter(None, parts):
            link = re.fullmatch(r"\[([^\]]+)\]\(([^\s)]+)\)", part)
            target = p
            if link:
                label, url = link.groups()
                if url not in links:
                    ident = f"rId{len(links) + 2}"
                    links[url] = ident
                    E.SubElement(relationships, "Relationship", Id=ident, Type=R + "/hyperlink", Target=url, TargetMode="External")
                target = E.SubElement(p, f"{{{W}}}hyperlink", {f"{{{R}}}id": links[url]})
                part = label
            r = node(target, "r")
            props = node(r, "rPr")
            if mono or part.startswith("`"):
                node(props, "rFonts", {"ascii": "Consolas", "hAnsi": "Consolas"})
                if part.startswith("`"):
                    part = part[1:-1]
            if part.startswith("**"):
                node(props, "b")
                part = part[2:-2]
            if link:
                node(props, "color", {"val": "175C91"})
                node(props, "u", {"val": "single"})
            t = node(r, "t", text=part.replace("&#124;", "|"))
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    lines = markdown.splitlines()
    i = 0
    code = False
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith("```"):
            code = not code
            continue
        if not line.strip():
            continue
        if line.startswith("| ") and not code:
            rows = [line]
            while i < len(lines) and lines[i].startswith("| "):
                rows.append(lines[i]); i += 1
            table = node(body, "tbl")
            props = node(table, "tblPr")
            node(props, "tblStyle", {"val": "TableGrid"})
            node(props, "tblW", {"w": "0", "type": "auto"})
            for ri, row in enumerate(rows):
                if re.fullmatch(r"[| :\-]+", row):
                    continue
                tr = node(table, "tr")
                if ri == 0:
                    node(node(tr, "trPr"), "tblHeader")
                for cell in row.strip().strip("|").split("|"):
                    tc = node(tr, "tc")
                    if ri == 0:
                        node(node(tc, "tcPr"), "shd", {"fill": "E3EDF5"})
                    runs(node(tc, "p"), cell.strip())
            continue
        p = node(body, "p")
        heading = re.match(r"^(#{1,4}) (.*)$", line)
        if heading and not code:
            level = len(heading[1])
            node(node(p, "pPr"), "pStyle", {"val": "Title" if level == 1 else f"Heading{level - 1}"})
            line = heading[2]
        elif line.startswith("- ") and not code:
            line = "• " + line[2:]
        runs(p, line, mono=code)
    section = node(body, "sectPr")
    node(section, "pgSz", {"w": 12240, "h": 15840})
    node(section, "pgMar", {"top": 1008, "right": 1008, "bottom": 1008, "left": 1008, "header": 360, "footer": 360})
    styles = E.Element(f"{{{W}}}styles")
    defaults = node(styles, "docDefaults")
    rp = node(node(defaults, "rPrDefault"), "rPr")
    node(rp, "rFonts", {"ascii": "Calibri", "hAnsi": "Calibri"})
    node(rp, "sz", {"val": 21})
    pp = node(node(defaults, "pPrDefault"), "pPr")
    node(pp, "spacing", {"after": 120})
    for name, size in [("Title", 36), ("Heading1", 28), ("Heading2", 25), ("Heading3", 22)]:
        st = node(styles, "style", {"type": "paragraph", "styleId": name})
        node(st, "name", {"val": name})
        node(node(st, "pPr"), "keepNext")
        r = node(st, "rPr"); node(r, "b"); node(r, "sz", {"val": size})
    st = node(styles, "style", {"type": "table", "styleId": "TableGrid"})
    borders = node(node(st, "tblPr"), "tblBorders")
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        node(borders, side, {"val": "single", "sz": 4, "color": "B8C5D0"})
    content = b'''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    rels = E.Element("Relationships", xmlns=PKG)
    E.SubElement(rels, "Relationship", Id="rId1", Type=R + "/officeDocument", Target="word/document.xml")
    result = io.BytesIO()
    with ZipFile(result, "w") as z:
        for path, data in {"[Content_Types].xml": content, "_rels/.rels": xml(rels),
                           "word/document.xml": xml(doc), "word/styles.xml": xml(styles),
                           "word/_rels/document.xml.rels": xml(relationships)}.items():
            info = ZipInfo(path, (2026, 9, 11, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, data)
    return result.getvalue()


def validate_inputs():
    for rec in json.loads((ROOT / "history/inputs.json").read_text()):
        if digest((ROOT / rec["path"]).read_bytes()) != rec["sha256"]:
            raise ValueError(f"Historical input changed: {rec['path']}")
    baseline = json.loads((ROOT / "stage0/baseline.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", baseline["implementation"]["revision"]):
        raise ValueError("Missing full implementation revision")
    inventory = json.loads((ROOT / "stage0/inventory.json").read_text())
    ids = [r["id"] for r in inventory["tests"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate test IDs")
    described = set()
    for ident, suffixes in re.findall(r"(S0-LL\d\d)-([a-z](?:/[a-z])*)", (ROOT / "decisions.md").read_text()):
        described.update(ident + "-" + x for x in suffixes.split("/"))
    supplemental = {"G0-U1-a", "S0-ENGINE-a", "S0-CONTRACTS-a", "S0-ABI-selection"}
    if not supplemental.issubset(ids):
        raise ValueError("Missing current Gate 0 or outline-exit record")
    if described != set(ids) - supplemental:
        raise ValueError(f"D7/inventory IDs disagree: {described.symmetric_difference(set(ids) - supplemental)}")
    for ident in supplemental - {"G0-U1-a"}:
        if ident not in (ROOT / "decisions.md").read_text():
            raise ValueError(f"Outline-exit test absent from D7: {ident}")
    for rec in inventory["tests"]:
        if not rec["assertions"] or not rec["variants"]:
            raise ValueError(f"Empty contract: {rec['id']}")
        for dep in rec["prerequisites"]:
            if dep not in ids:
                raise ValueError(f"Unknown prerequisite: {dep}")
    policy = json.loads((ROOT / "stage0/benchmarks.json").read_text())
    measurements = json.loads((ROOT / "stage0/measurement-inventory.json").read_text())
    wanted = {(candidate, workload) for candidate in policy["candidates"] for workload in policy["workloads"]}
    actual = [(m["candidate"], m["workload"]) for m in measurements["measurements"]]
    if set(actual) != wanted or len(actual) != len(wanted):
        raise ValueError("Measurement inventory does not cover each candidate/workload exactly once")
    for source, version in [("outline.md", "0.14"), ("acceptance.md", "1.4"), ("decisions.md", "1.5")]:
        if f"VERSION {version} " not in (ROOT / source).read_text().splitlines()[0]:
            raise ValueError(f"Wrong document version: {source}")
    baseline = json.loads((ROOT / "stage0/baseline.json").read_text())
    gate0 = next(t for t in inventory["tests"] if t["id"] == "G0-U1-a")
    if baseline.get("reference_platform") != "macOS" or gate0["variants"] != ["macos-x86-64"]:
        raise ValueError("Native reference and Gate 0 must consistently select macOS")
    # Check all local Markdown links, including generated DOCX names after generation.
    for path in ROOT.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", path.read_text()):
            if "://" not in target and not target.startswith("#"):
                if not (path.parent / target.split("#")[0]).exists():
                    raise ValueError(f"Broken local link in {path.name}: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "check"])
    args = parser.parse_args()
    generated = projections()
    for name, output in DOCS.items():
        generated[output] = docx_bytes(generated.get(name, (ROOT / name).read_bytes()).decode())
    manifest = {"generator": "tools/manage.py", "generator_sha256": digest(Path(__file__).read_bytes()),
                "documents": [{"source": src, "source_sha256": digest(generated.get(src, (ROOT / src).read_bytes())),
                               "output": dest, "output_sha256": digest(generated[dest])} for src, dest in DOCS.items()]}
    generated["documents.json"] = json_bytes(manifest)
    for name, data in generated.items():
        path = ROOT / name
        if args.command == "generate":
            path.write_bytes(data)
        elif not path.exists() or path.read_bytes() != data:
            raise ValueError(f"Stale generated projection: {name}; run generate")
    validate_inputs()
    print(f"PASS: document projections, LL schedule, D7 inventory, local links and original-input hashes ({args.command}).")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
