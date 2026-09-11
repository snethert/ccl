#!/usr/bin/env python3
"""Synthetic negative controls for the checkers; never CCL/compiler acceptance evidence."""
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

sys.dont_write_bytecode = True


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load("gate", "gate.py")
census = load("census", "check-census.py")
evidence = load("evidence", "check-evidence.py")
ROOT = Path(__file__).resolve().parents[1]
revision = json.loads((ROOT / "stage0/baseline.json").read_text())["implementation"]["revision"]
count = 0


def expect(actual, wanted, label):
    global count
    assert actual == wanted, f"{label}: expected {wanted}, got {actual}"
    count += 1


with tempfile.TemporaryDirectory(prefix="ccl-wasm-control-") as tmp:
    path = Path(tmp)
    (path / "fixture").write_text("synthetic validator control; not production evidence")
    artifacts = [{"role": r, "path": "fixture", "sha256": gate.sha256(path / "fixture")} for r in ["implementation", "test", "schema", "log"]]
    inventory = {"source_revision": revision, "required_record_roles": [a["role"] for a in artifacts], "tests": [
        {"id": "CONTROL-fixture", "source_revision": revision, "runner": "synthetic-control", "evidence_kind": "CONTROL EXECUTION", "variants": ["fixture"], "assertions": [{"id": "value"}], "prerequisites": []}]}
    record = {"id": "CONTROL-fixture", "variant": "fixture", "source_revision": revision, "evidence_kind": "CONTROL EXECUTION", "status": "PASS", "assertions": [{"id": "value", "status": "PASS"}], "artifacts": artifacts, "substitutions": [], "skips": [], "review_disposition": "ACCEPTED", "review_record": "synthetic control only"}
    record.update({k: "synthetic-control" for k in ["command", "toolchain", "engine", "timestamp", "configuration", "seed", "test_revision"]})
    report = {"version": 1, "source_revision": revision, "inventory_sha256": "a" * 64, "results": [record]}
    check = lambda r: gate.assess(inventory, r, "a" * 64, path)[0]
    expect(check(report), "PASS", "well-formed synthetic checker fixture")
    for field in ["variants", "assertions"]:
        saved = inventory["tests"][0][field]
        inventory["tests"][0][field] = []
        expect(check(report), "FAIL", f"empty required {field}")
        inventory["tests"][0][field] = saved
    mutant = copy.deepcopy(report); mutant["results"] = []
    expect(check(mutant), "BLOCKED", "missing expected test")
    mutant = copy.deepcopy(report); mutant["inventory_sha256"] = "b" * 64
    expect(check(mutant), "FAIL", "stale inventory")
    for field, value, wanted in [("status", "FAIL", "FAIL"), ("evidence_kind", "SOURCE INSPECTION", "FAIL"), ("source_revision", "0" * 40, "FAIL"), ("skips", ["skip"], "FAIL"), ("review_disposition", "NOT_REVIEWED", "BLOCKED")]:
        mutant = copy.deepcopy(report); mutant["results"][0][field] = value
        expect(check(mutant), wanted, field)
    mutant = copy.deepcopy(report); mutant["results"][0]["assertions"] = []
    expect(check(mutant), "FAIL", "discarded assertion")
    mutant = copy.deepcopy(report); mutant["results"].append(copy.deepcopy(record))
    expect(check(mutant), "FAIL", "duplicate evidence")
    mutant = copy.deepcopy(report); mutant["results"][0]["artifacts"][0]["path"] = "../escaped"
    expect(check(mutant), "FAIL", "escaping artifact")
    generic_inventory = copy.deepcopy(inventory)
    generic_inventory["tests"][0]["variants"] = ["full:C", "full:C4", "full:B"]
    generic_report = copy.deepcopy(report)
    generic_report["results"] = [dict(copy.deepcopy(record), variant=v) for v in generic_inventory["tests"][0]["variants"]]
    generic_check = lambda r: gate.assess(generic_inventory, r, "a" * 64, path)[0]
    expect(generic_check(generic_report), "PASS", "all required generic ABIs pass without H")
    mutant = copy.deepcopy(generic_report); mutant["results"].pop()
    expect(generic_check(mutant), "BLOCKED", "missing required generic ABI still blocks")
    mutant = copy.deepcopy(generic_report); mutant["results"].pop(); mutant["results"].append(dict(copy.deepcopy(record), variant="full:H(G)"))
    expect(generic_check(mutant), "BLOCKED", "future H variant cannot substitute for required evidence")
    (path / "fixture").write_text("mutated after execution")
    expect(check(report), "FAIL", "stale retained artifact")


def n(ident, kind):
    return {"id": ident, "kind": kind, "disposition": "implemented", "required": True, "implementation": "synthetic-only", "evidence": "synthetic fixture, not source evidence", "tests": ["S0-LL15-b"], "reason": ""}


def edge(a, b):
    return {"from": a, "targets": [b], "phase": "load", "origin": "conservative", "resolution": "complete", "evidence": "synthetic expected edge"}


graph = {"version": 1, "source_revision": revision, "profile": "synthetic-control", "instrumentation_sha256": "a" * 64, "inputs_sha256": "b" * 64, "trace_sha256": "c" * 64, "seed_review": "synthetic checker control", "seeds": ["module"], "nodes": [n("module", "module"), n("init-a", "initializer"), n("init-b", "initializer")], "edges": [edge("module", "init-a"), edge("init-a", "init-b")], "initializers": [{"node": "init-a", "prerequisites": [], "rank": 0, "completion_assertion": "a"}, {"node": "init-b", "prerequisites": ["init-a"], "rank": 1, "completion_assertion": "b"}], "observed_modules": ["module"], "unobserved_modules": []}
expect(census.validate(graph), [], "well-formed synthetic graph")
mutations = [
    lambda x: x["nodes"].pop(),
    lambda x: x["edges"].pop(),
    lambda x: x["edges"][0].update(resolution="unresolved"),
    lambda x: x.update(seeds=[]),
    lambda x: x["initializers"][0].update(prerequisites=["init-b"]),
    lambda x: x["nodes"][1].update(disposition="unsupported"),
    lambda x: x.update(observed_modules=[]),
    lambda x: x.update(source_revision="0" * 40),
    lambda x: x["nodes"].append(copy.deepcopy(x["nodes"][0])),
    lambda x: x.update(version=True),
    lambda x: x.update(invented_field=True),
]
for index, mutate in enumerate(mutations):
    mutant = copy.deepcopy(graph); mutate(mutant)
    expect(bool(census.validate(mutant)), True, f"graph rejection mutant {index}")

# Exercise the retained-evidence currency bug with actual archived envelopes.
with tempfile.TemporaryDirectory(prefix="ccl-wasm-evidence-control-") as tmp:
    root = Path(tmp)
    (root / 'stage0').mkdir(); (root / 'evidence').mkdir()
    (root / 'stage0/inventory.json').write_text('{"fixture": "current"}')
    current = evidence.digest(root / 'stage0/inventory.json')
    with ZipFile(root / 'pack.zip', 'w') as archive:
        archive.writestr('results.json', json.dumps({'inventory_sha256': current}))
    rec = {'id': 'CONTROL-retained', 'path': 'pack.zip', 'sha256': evidence.digest(root / 'pack.zip'),
           'currency': 'CURRENT', 'inventory_sha256': current, 'results_member': 'results.json'}
    evidence.ROOT = root
    def retained(record):
        (root / 'evidence/index.json').write_text(json.dumps({'current_runs': [record]}))
        try:
            evidence.check()
            return 'PASS'
        except ValueError:
            return 'FAIL'
    expect(retained(rec), 'PASS', 'current archive and index agree')
    expect(retained({**rec, 'inventory_sha256': '0' * 64}), 'FAIL', 'stale index labeled CURRENT')
    with ZipFile(root / 'pack.zip', 'w') as archive:
        archive.writestr('results.json', json.dumps({'inventory_sha256': '0' * 64}))
    expect(retained({**rec, 'sha256': evidence.digest(root / 'pack.zip')}), 'FAIL', 'old archive relabeled with a current index hash')
print(f"PASS: {count} synthetic checker positive/negative controls; no production acceptance claim.")
