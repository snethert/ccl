#!/usr/bin/env python3
"""Build a single hypercompact text artifact from core-multipage HTML."""

from __future__ import annotations

import argparse
import gzip
import re
from html.parser import HTMLParser
from pathlib import Path


BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "aside",
    "blockquote",
    "pre",
    "li",
    "ul",
    "ol",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "dt",
    "dd",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "br",
}


class MainBodyTextExtractor(HTMLParser):
    """Extract plain text from the Sphinx main body (`div.body[role=main]`)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_main_body = False
        self._main_body_depth = 0
        self._ignore_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {k: (v or "") for k, v in attrs}
        classes = set(attrs_map.get("class", "").split())
        role = attrs_map.get("role", "")

        if not self._in_main_body and tag == "div" and "body" in classes and role == "main":
            self._in_main_body = True
            self._main_body_depth = 1
            return

        if self._in_main_body:
            if tag == "div":
                self._main_body_depth += 1
            if tag in {"script", "style", "noscript"}:
                self._ignore_depth += 1
            if tag in BLOCK_TAGS:
                self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._in_main_body:
            if tag in {"script", "style", "noscript"} and self._ignore_depth > 0:
                self._ignore_depth -= 1
            if tag in BLOCK_TAGS:
                self._parts.append("\n")
            if tag == "div":
                self._main_body_depth -= 1
                if self._main_body_depth <= 0:
                    self._in_main_body = False

    def handle_data(self, data: str) -> None:
        if self._in_main_body and self._ignore_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        lines = [re.sub(r" +", " ", line).strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines).strip()


def collect_html_files(root: Path) -> list[Path]:
    files = sorted(root.rglob("*.html"))
    skipped = {"search.html", "genindex.html"}
    selected: list[Path] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel.startswith("_static/"):
            continue
        if path.name in skipped:
            continue
        selected.append(path)
    return selected


def build_hypercompact(source_root: Path, output_file: Path, output_gzip: Path) -> tuple[int, int]:
    docs: list[str] = []
    files = collect_html_files(source_root)

    for path in files:
        rel = path.relative_to(source_root).as_posix()
        parser = MainBodyTextExtractor()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        parser.close()
        extracted = parser.get_text()
        if not extracted:
            continue
        docs.append(f"### {rel}\n{extracted}\n")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged = "\n".join(docs).strip() + "\n"
    output_file.write_text(merged, encoding="utf-8")

    with gzip.open(output_gzip, "wb", compresslevel=9) as gz:
        gz.write(merged.encode("utf-8"))

    return len(files), len(merged.encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        default="doc/wasm/spec/core-multipage",
        help="Path to the mirrored multi-page core spec HTML root.",
    )
    parser.add_argument(
        "--output",
        default="doc/wasm/spec/core-hypercompact.txt",
        help="Output consolidated text file.",
    )
    parser.add_argument(
        "--output-gzip",
        default="doc/wasm/spec/core-hypercompact.txt.gz",
        help="Output gzipped consolidated text file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root)
    output_file = Path(args.output)
    output_gzip = Path(args.output_gzip)

    if not source_root.exists():
        raise SystemExit(f"error: source root not found: {source_root}")

    file_count, merged_bytes = build_hypercompact(source_root, output_file, output_gzip)
    print(
        "Generated hypercompact spec: "
        f"{output_file} ({merged_bytes} bytes), "
        f"{output_gzip}, "
        f"from {file_count} HTML files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
