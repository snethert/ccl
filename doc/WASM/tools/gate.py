#!/usr/bin/env python3
"""Check a frozen test inventory against retained evidence. Exit 0/1/2 = PASS/FAIL/BLOCKED."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess(inventory, report, inventory_hash, evidence_root):
    failures, blocked = [], []
    if report.get("inventory_sha256") != inventory_hash:
        failures.append("inventory hash mismatch")
    if report.get("source_revision") != inventory["source_revision"]:
        failures.append("implementation revision mismatch")
    if report.get("version") != 1 or not isinstance(report.get("results"), list):
        return "FAIL", ["invalid result envelope"]
    records = {}
    for result in report["results"]:
        if not isinstance(result, dict):
            failures.append("non-object result"); continue
        key = (result.get("id"), result.get("variant"))
        if key in records:
            failures.append(f"duplicate result {key}")
        records[key] = result
        if result.get("status") == "FAIL":
            failures.append(f"failed execution {key}")
    expected_ids = [r["id"] for r in inventory["tests"]]
    if not expected_ids or len(expected_ids) != len(set(expected_ids)):
        return "FAIL", ["empty or duplicate required inventory"]
    if not inventory.get("required_record_roles"):
        return "FAIL", ["empty artifact-role inventory"]
    for test in inventory["tests"]:
        if not test.get("variants") or len(set(test["variants"])) != len(test["variants"]):
            return "FAIL", [f"empty or duplicate variants for {test['id']}"]
        assertions = [a["id"] for a in test.get("assertions", [])]
        if not assertions or len(set(assertions)) != len(assertions):
            return "FAIL", [f"empty or duplicate assertion inventory for {test['id']}"]
        if any(dep not in expected_ids for dep in test.get("prerequisites", [])):
            return "FAIL", [f"unknown prerequisite for {test['id']}"]
    for test in inventory["tests"]:
        for variant in test["variants"]:
            label = f"{test['id']} [{variant}]"
            result = records.get((test["id"], variant))
            if result is None:
                blocked.append(f"missing {label}"); continue
            if result.get("status") != "PASS":
                blocked.append(f"non-passing {label}"); continue
            if not test.get("runner"):
                blocked.append(f"no identified acceptance runner for {label}")
            if result.get("source_revision") != test["source_revision"]:
                failures.append(f"wrong source revision: {label}")
            if result.get("evidence_kind") != test["evidence_kind"]:
                failures.append(f"wrong evidence kind: {label}")
            if result.get("substitutions") != [] or result.get("skips") != []:
                failures.append(f"substitution/skip or missing disclosure: {label}")
            if variant.endswith("H(G)") and result.get("generic_abi") not in ["B", "C", "C4"]:
                failures.append(f"unspecified hybrid generic ABI: {label}")
            wanted = {a["id"] for a in test["assertions"]}
            got = result.get("assertions", [])
            if not isinstance(got, list) or any(not isinstance(a, dict) for a in got):
                failures.append(f"invalid assertions: {label}"); continue
            if len(got) != len(wanted) or {a.get("id") for a in got} != wanted or any(a.get("status") != "PASS" for a in got):
                failures.append(f"missing/failed/duplicate assertions: {label}")
            roles = set()
            artifacts = result.get("artifacts", [])
            if not isinstance(artifacts, list):
                failures.append(f"invalid artifacts: {label}"); artifacts = []
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    failures.append(f"invalid artifact: {label}"); continue
                path = (evidence_root / artifact.get("path", "")).resolve()
                expected = artifact.get("sha256", "")
                if (not path.is_relative_to(evidence_root.resolve()) or not path.is_file()
                        or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                        or sha256(path) != expected):
                    failures.append(f"missing/mismatched/escaping artifact: {label}")
                roles.add(artifact.get("role"))
            if not set(inventory["required_record_roles"]).issubset(roles):
                failures.append(f"missing artifact roles: {label}")
            for field in ["command", "toolchain", "engine", "timestamp", "configuration", "seed", "test_revision"]:
                if result.get(field) is None or result.get(field) == "":
                    failures.append(f"missing {field}: {label}")
            if result.get("review_disposition") != "ACCEPTED" or not result.get("review_record"):
                blocked.append(f"unreviewed {label}")
    if failures:
        return "FAIL", failures + blocked
    return ("BLOCKED", blocked) if blocked else ("PASS", [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text())
    report = json.loads(args.results.read_text())
    status, reasons = assess(inventory, report, sha256(args.inventory), args.results.parent)
    print(json.dumps({"status": status, "reasons": reasons}, indent=2))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[status]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "reasons": [str(exc)]}))
        sys.exit(1)
