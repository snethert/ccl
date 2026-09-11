#!/usr/bin/env python3
"""Materialize an explicitly authorized, scoped acceptance decision in a new envelope."""
import argparse
import copy
import json
from pathlib import Path
from evidence_binding import binding_errors, digest, safe_path
from gate import assess


def accept(source, inventory_path, decision_path, review_path, output):
    source, output = source.resolve(), output.resolve()
    if output.exists() or (output.parent.exists() and any(output.parent.iterdir())):
        raise ValueError('acceptance destination must be new and empty')
    report_bytes, decision_bytes, review_bytes = source.read_bytes(), decision_path.read_bytes(), review_path.read_bytes()
    report, decision = json.loads(report_bytes), json.loads(decision_bytes)
    inventory = json.loads(inventory_path.read_text())
    if type(decision.get('version')) is not int or decision['version'] != 1 or decision.get('operation') != 'PROJECT_ACCEPTANCE_NO_EXECUTION':
        raise ValueError('unsupported acceptance decision')
    for field in ['authorization', 'timestamp', 'review_commit', 'scope', 'exclusions']:
        if not decision.get(field): raise ValueError('missing decision field: ' + field)
    if decision.get('source_report_sha256') != digest(report_bytes) or decision.get('review_sha256') != digest(review_bytes):
        raise ValueError('acceptance decision does not identify the original evidence and review')
    files = {}
    def read(name):
        path = (source.parent / safe_path(name)).resolve()
        if not path.is_relative_to(source.parent): raise ValueError('escaping evidence artifact')
        return path.read_bytes()
    errors = binding_errors(inventory, report, read)
    if errors: raise ValueError('; '.join(errors))
    status, reasons = assess(inventory, report, digest(inventory_path.read_bytes()), source.parent)
    if status == 'FAIL': raise ValueError('invalid execution evidence: ' + '; '.join(reasons))
    records = {}
    for r in report['results']:
        key = (r['id'], r['variant'])
        if key in records: raise ValueError('duplicate execution record')
        records[key] = r
        for a in r['artifacts']:
            data = read(a['path'])
            if digest(data) != a['sha256']: raise ValueError('artifact mismatch: ' + a['path'])
            files[a['path']] = data
        name = r['contract_binding']['inventory_path']; files[name] = read(name)
    selected = set()
    for approval in decision.get('records', []):
        key = (approval['id'], approval['variant'])
        if key in selected or key not in records: raise ValueError('duplicate or unknown acceptance target')
        r = records[key]
        if (r['status'] != 'PASS' or r.get('skips') != [] or r.get('substitutions') != []
            or not approval.get('scope') or approval.get('test_revision') != r['test_revision']
            or approval.get('contract_sha256') != r['contract_binding']['contract_sha256']):
            raise ValueError('acceptance target differs from authorized passing evidence')
        selected.add(key)
    if not selected: raise ValueError('empty acceptance decision')
    extra = {'acceptance/decision.json': (decision_bytes, 'log'), 'acceptance/review.md': (review_bytes, 'log'),
             'acceptance/original-results.json': (report_bytes, 'log'),
             'acceptance/producer.py': (Path(__file__).read_bytes(), 'test')}
    if set(extra) & set(files): raise ValueError('acceptance provenance collides with original artifacts')
    files.update({k: v[0] for k, v in extra.items()})
    if output.name in files: raise ValueError('acceptance output collides with original artifact')
    result = copy.deepcopy(report)
    for r in result['results']:
        if (r['id'], r['variant']) in selected:
            r['review_disposition'] = 'ACCEPTED'
            r['review_record'] = 'acceptance/decision.json'
            r['artifacts'].extend({'path': k, 'sha256': digest(v), 'role': role} for k, (v, role) in extra.items())
    result['acceptance_provenance'] = {'operation': decision['operation'], 'decision': 'acceptance/decision.json',
                                     'original_report_sha256': digest(report_bytes), 'review_commit': decision['review_commit']}
    output.parent.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = output.parent / safe_path(name); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    output.write_text(json.dumps(result, indent=2) + '\n')
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['results', 'inventory', 'decision', 'review', 'output']: p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    print(accept(args.results, args.inventory, args.decision, args.review, args.output))
