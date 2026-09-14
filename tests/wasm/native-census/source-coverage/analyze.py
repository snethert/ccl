"""Static source-coverage accounting for the Wasm census.

Produces surface counts over pristine U1 source describing how much of the
source the census must eventually account for, and how much of it a single
native darwinx8664 observation run can never read.

This is analysis, not evidence of execution. It confers no gate credit and
discharges no S0 obligation. See
``doc/WASM/stage0/source-coverage-analysis.md`` for scope and limits.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexer import scan  # noqa: E402

SUBTREES = ("level-0", "level-1", "lib", "library", "compiler", "xdump", "tools")
# Subtrees whose modules a cold boot loads. `tools` (ASDF, defsystem, sockets)
# is compiled into the tree but reached only through REQUIRE, so a boot
# observation sees none of it; it is counted separately rather than folded
# into the cold-start denominator.
SUBTREES_COLD = ("level-0", "level-1", "lib", "library", "compiler", "xdump")

# Files whose path marks them as belonging to a target the x8664 build does
# not compile. Conservative: a file is excluded only on an unambiguous
# architecture marker in its path.
OTHER_TARGET = re.compile(
    r"(?i)(^|/)(PPC|ARM|X8632)(/|$)"
    r"|(^|/)(x?(ppc|arm)[0-9]*|x8632|xppc|xarm)[a-z0-9-]*\.lisp$"
    r"|(^|/)[a-z0-9-]*(ppc32|ppc64|arm64)[a-z0-9-]*\.lisp$"
)

# Approximate *features* of a v1.13 darwinx8664 image. Used only to classify
# reader-conditional branches as read or unread; a misclassified feature moves
# a site between two reported buckets and is visible in the per-feature table.
DARWIN_X8664_FEATURES = frozenset("""
ccl clozure openmcl common-lisp ansi-cl x3j13 mcl
x86-target x8664-target x86 x8664
darwin-target darwinx8664-target darwinx86-target darwin unix
64-bit-target little-endian-target 64-bit-host
openmcl-native-threads openmcl-partial-mop openmcl-unicode-strings
""".split())

COND = re.compile(r"#([-+])([A-Za-z0-9:.*%_-]+|\()")
# Constructs that resist both a single observation run and a naive traversal.
CONSTRUCTS = {
    "read_time_eval": r"#\.",
    "eval_call": r"\(eval\b",
    "compile_call": r"\(compile\b",
    "require": r"\(require\b",
    "load_time_value": r"\bload-time-value\b",
    "read_from_string": r"\bread-from-string\b",
    "intern": r"\(intern\b",
    "find_symbol": r"\bfind-symbol\b",
    "symbol_function": r"\bsymbol-function\b",
    "fdefinition": r"\bfdefinition\b",
    "make_load_form": r"\bmake-load-form\b",
    "defcallback": r"\bdefcallback\b",
    "ff_call": r"\bff-call\b",
    "external_call": r"\bexternal-call\b",
    "macptr": r"\bmacptr\b",
    "defloadvar": r"\bdefloadvar\b",
    "def_ccl_pointers": r"\bdef-ccl-pointers\b",
    "set_macro_character": r"\bset-(dispatch-)?macro-character\b",
    "defmethod": r"\(defmethod\b",
    "defgeneric": r"\(defgeneric\b",
    "define_condition": r"\(define-condition\b",
    "no_applicable_method": r"\bno-applicable-method\b",
    "unwind_protect": r"\bunwind-protect\b",
    "without_interrupts": r"\bwithout-interrupts\b",
    "current_tcr": r"%current-tcr\b",
    "stack_block": r"%stack-block\b",
    "deffaslop": r"\(deffaslop\b",
    "defxloadfaslop": r"\(defxloadfaslop\b",
    "target_symbol_ref": r"\btarget::[a-zA-Z0-9%$*.<>=/+-]+",
}
CONSTRUCTS = {k: re.compile(v) for k, v in CONSTRUCTS.items()}


def sources(root):
    for sub in SUBTREES:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dp, _dn, fn in os.walk(base):
            for f in sorted(fn):
                if f.endswith(".lisp"):
                    p = os.path.join(dp, f)
                    yield os.path.relpath(p, root).replace(os.sep, "/")


def classify_conditionals(text):
    """Split reader-conditional sites into read / unread under darwinx8664."""
    read = unread = compound = 0
    unread_by_feature = {}
    for m in COND.finditer(text):
        sign, feat = m.group(1), m.group(2).lower().lstrip(":")
        if feat == "(":
            compound += 1
            continue
        present = feat in DARWIN_X8664_FEATURES
        if present if sign == "+" else not present:
            read += 1
        else:
            unread += 1
            k = "#%s%s" % (sign, feat)
            unread_by_feature[k] = unread_by_feature.get(k, 0) + 1
    return read, unread, compound, unread_by_feature


def analyze(root):
    corpus = {"all": {}, "x8664": {}, "x8664_cold": {}}
    for key in corpus:
        corpus[key] = {
            "files": 0, "forms": 0, "reader_cond": 0, "reader_cond_top": 0,
            "cond_read": 0, "cond_unread": 0, "cond_compound": 0,
            "heads": {}, "constructs": {k: 0 for k in CONSTRUCTS},
        }
    unread_by_feature = {}
    per_dir = {}
    digest = hashlib.sha256()

    for rel in sorted(sources(root)):
        text = open(os.path.join(root, rel), encoding="utf-8",
                    errors="replace").read()
        digest.update(rel.encode() + b"\0")
        digest.update(hashlib.sha256(text.encode("utf-8", "replace")).digest())

        s = scan(text)
        read, unread, compound, byfeat = classify_conditionals(text)
        hits = {k: len(r.findall(text)) for k, r in CONSTRUCTS.items()}
        in_x8664 = not OTHER_TARGET.search(rel)

        keys = ["all"]
        if in_x8664:
            keys.append("x8664")
            if rel.split("/")[0] in SUBTREES_COLD:
                keys.append("x8664_cold")
        for key in keys:
            c = corpus[key]
            c["files"] += 1
            c["forms"] += s["forms"]
            c["reader_cond"] += s["reader_cond"]
            c["reader_cond_top"] += s["reader_cond_top"]
            c["cond_read"] += read
            c["cond_unread"] += unread
            c["cond_compound"] += compound
            for h in s["heads"]:
                c["heads"][h] = c["heads"].get(h, 0) + 1
            for k, v in hits.items():
                c["constructs"][k] += v

        if in_x8664 and rel.split("/")[0] in SUBTREES_COLD:
            for k, v in byfeat.items():
                unread_by_feature[k] = unread_by_feature.get(k, 0) + v
            d = rel.split("/")[0]
            per_dir.setdefault(d, {"files": 0, "forms": 0})
            per_dir[d]["files"] += 1
            per_dir[d]["forms"] += s["forms"]

    for c in corpus.values():
        c["distinct_heads"] = len(c["heads"])
        c["heads"] = dict(sorted(c["heads"].items(), key=lambda kv: -kv[1])[:50])

    return {
        "kind": "static-source-coverage",
        "status": "EXECUTED_ANALYSIS",
        "gate_credit": False,
        "discharges_obligation": None,
        "baseline_revision": "c994217adc56b3f8a564526cee4695893ac84d86",
        "head": subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip(),
        "subtrees": list(SUBTREES),
        "subtrees_cold": list(SUBTREES_COLD),
        "corpus_sha256": digest.hexdigest(),
        "assumed_features": sorted(DARWIN_X8664_FEATURES),
        "totals": corpus,
        "x8664_per_directory": dict(sorted(per_dir.items())),
        "x8664_cold_unread_conditionals_by_feature": dict(
            sorted(unread_by_feature.items(), key=lambda kv: -kv[1])[:40]),
        "traversed_so_far": {
            "source": "doc/WASM/stage0/source-traversal.md",
            "files": 1,
            "forms": 16,
            "note": "lib/dumplisp.lisp, all top-level forms accounted for "
                    "through EOF; 8 of 12 definitions stopped at a target gap",
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "..", "..")))
    ap.add_argument("--output")
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()

    result = analyze(a.root)
    # 'head' varies with the checkout; exclude it from the determinism check.
    text = json.dumps({k: v for k, v in result.items() if k != "head"}
                      if a.stdout else result, indent=2, sort_keys=True)
    if a.output:
        os.makedirs(os.path.dirname(a.output) or ".", exist_ok=True)
        open(a.output, "w").write(text + "\n")
        t = result["totals"]
        print("x8664 slice: %d files, %d top-level forms, %d unread "
              "reader-conditional sites"
              % (t["x8664"]["files"], t["x8664"]["forms"],
                 t["x8664"]["cond_unread"]))
        print("corpus sha256: %s" % result["corpus_sha256"])
        print("wrote %s" % a.output)
    else:
        print(text)


if __name__ == "__main__":
    main()
