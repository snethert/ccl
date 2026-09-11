#!/usr/bin/env python3
"""Validate the census exchange schema and conservative closure; not instrumentation completeness."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def shape(value, schema, definitions, where="$", errors=None):
    """Validate the exact JSON Schema keywords used by the checked-in exchange schema."""
    errors = [] if errors is None else errors
    if "$ref" in schema:
        return shape(value, definitions[schema["$ref"].rsplit("/", 1)[-1]], definitions, where, errors)
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    allowed = schema.get("type", list(kinds))
    allowed = [allowed] if isinstance(allowed, str) else allowed
    if not any(type(value) is kinds[k] for k in allowed):
        errors.append(f"{where}: wrong type"); return errors
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(f"{where}: wrong constant")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: outside enum")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}.{key}: missing")
        if schema.get("additionalProperties") is False and set(value) - set(props):
            errors.append(f"{where}: unknown properties {sorted(set(value) - set(props))}")
        for key, val in value.items():
            if key in props:
                shape(val, props[key], definitions, where + "." + key, errors)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: too few items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append(f"{where}: duplicate items")
        for i, val in enumerate(value):
            shape(val, schema.get("items", {}), definitions, f"{where}[{i}]", errors)
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or ("pattern" in schema and not re.search(schema["pattern"], value)):
            errors.append(f"{where}: invalid string")
    if type(value) is int and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{where}: below minimum")
    return errors


def validate(graph):
    schema = json.loads((ROOT / "contracts/census.schema.json").read_text())
    errors = shape(graph, schema, schema["$defs"])
    if errors:
        return errors
    baseline = json.loads((ROOT / "stage0/baseline.json").read_text())
    if graph["source_revision"] != baseline["implementation"]["revision"]:
        errors.append("census is not for the implementation baseline")
    nodes = {n["id"]: n for n in graph["nodes"]}
    if len(nodes) != len(graph["nodes"]):
        errors.append("duplicate node identity")
    known_tests = {n["id"] for n in json.loads((ROOT / "stage0/inventory.json").read_text())["tests"]}
    for n in nodes.values():
        if not set(n["tests"]).issubset(known_tests):
            errors.append(f"unknown regression ID: {n['id']}")
    refs = graph["seeds"] + graph["observed_modules"] + [n["node"] for n in graph["unobserved_modules"]]
    for edge in graph["edges"]:
        refs.extend([edge["from"]] + edge["targets"])
        if edge["resolution"] == "complete" and not edge["targets"]:
            errors.append("complete edge has no candidate target")
    if set(refs) - set(nodes):
        errors.append(f"missing nodes: {sorted(set(refs) - set(nodes))}")
        return errors
    reachable = set(graph["seeds"])
    changed = True
    while changed:
        old = len(reachable)
        for edge in graph["edges"]:
            if edge["from"] in reachable:
                reachable.update(edge["targets"])
        changed = old != len(reachable)
    for edge in graph["edges"]:
        if edge["from"] in reachable and edge["resolution"] != "complete":
            errors.append(f"unresolved reachable edge from {edge['from']}")
    for ident in reachable:
        n = nodes[ident]
        if n["disposition"] == "unresolved" or not n["implementation"]:
            errors.append(f"unimplemented reachable node {ident}")
        if n["required"] and n["disposition"] == "unsupported":
            errors.append(f"unsupported required dependency {ident}")
        if n["disposition"] == "unsupported" and not n["reason"]:
            errors.append(f"unexplained unsupported operation {ident}")
    for n in nodes.values():
        if n["required"] and n["id"] not in reachable:
            errors.append(f"required node outside closure {n['id']}")
    observed = set(graph["observed_modules"])
    unobserved = [n["node"] for n in graph["unobserved_modules"]]
    modules = {i for i in reachable if nodes[i]["kind"] == "module"}
    if observed - modules or set(unobserved) != modules - observed or len(unobserved) != len(set(unobserved)):
        errors.append("module trace reconciliation is incomplete or inconsistent")
    initializers = {i["node"]: i for i in graph["initializers"]}
    required_initializers = {i for i in reachable if nodes[i]["kind"] == "initializer"}
    if len(initializers) != len(graph["initializers"]) or set(initializers) != required_initializers:
        errors.append("initializer inventory differs from reachable initializers")
    for init in initializers.values():
        for dep in init["prerequisites"]:
            if dep not in initializers or initializers[dep]["rank"] >= init["rank"]:
                errors.append(f"invalid/cyclic initializer prerequisite {init['node']} -> {dep}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.graph.read_text()))
        print(json.dumps({"status": "FAIL" if errors else "PASS", "scope": "schema and graph invariants only", "errors": errors}, indent=2))
        sys.exit(1 if errors else 0)
    except (KeyError, ValueError, TypeError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
