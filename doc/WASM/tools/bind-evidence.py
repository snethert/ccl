#!/usr/bin/env python3
"""Produce a separate v2 envelope from verified evidence; never overwrite a run."""
import argparse
import json
from pathlib import Path
import shutil
from evidence_binding import bind_report, binding_errors, digest, safe_path


def read_artifact(root, name):
    path = (root / safe_path(name)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('escaping evidence artifact: ' + name)
    return path.read_bytes()


def bind(source, inventory_path, output, current=None, fresh=False):
    source, inventory_path, output = source.resolve(), inventory_path.resolve(), output.resolve()
    if output.exists():
        raise ValueError('never overwrite a retained evidence envelope')
    data, inventory_data = source.read_bytes(), inventory_path.read_bytes()
    report, original = json.loads(data), json.loads(inventory_data)
    target = json.loads(current.read_text()) if current else original
    if output.parent != source.parent and output.parent.exists() and any(output.parent.iterdir()):
        raise ValueError('migration destination must be empty')
    files = {}
    for record in report['results']:
        for artifact in record['artifacts']:
            payload = read_artifact(source.parent, artifact['path'])
            if digest(payload) != artifact['sha256']:
                raise ValueError('source artifact mismatch: ' + artifact['path'])
            files[artifact['path']] = payload
        if 'contract_binding' in record:
            name = record['contract_binding']['inventory_path']
            files[name] = read_artifact(source.parent, name)
    # The source report, immutable inventory and producer are content-addressed.
    extra = {
        'binding-source/' + digest(data) + '/report.json': (data, 'log'),
        'binding-source/' + digest(inventory_data) + '/inventory.json': (inventory_data, 'schema')}
    for filename in ['evidence_binding.py', 'bind-evidence.py']:
        payload = Path(__file__).with_name(filename).read_bytes()
        extra['binding-source/' + digest(payload) + '/' + filename] = (payload, 'test')
    snapshot = 'binding-source/' + digest(inventory_data) + '/inventory.json'
    bound = bind_report(report, original, snapshot, digest(inventory_data))
    available = dict(files, **{p: data for p, (data, _) in extra.items()})
    errors = binding_errors(target, bound, lambda name: available[name])
    if errors:
        raise ValueError('; '.join(errors))
    if output.name in available:
        raise ValueError('output would replace an original artifact')
    output.parent.mkdir(parents=True, exist_ok=True)
    for name, payload in available.items():
        path = output.parent / safe_path(name)
        if not path.resolve().is_relative_to(output.parent):
            raise ValueError('escaping destination artifact')
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError('never rewrite an existing evidence artifact: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    additions = [{'path': p, 'sha256': digest(data), 'role': role} for p, (data, role) in extra.items()]
    for record in bound['results']:
        record['artifacts'].extend(additions)
    bound['binding_provenance'] = {'operation': 'ATTACH_TO_NEW_REPORT' if fresh else 'FORMAT_UPGRADE_NO_EXECUTION',
        'source_report': additions[0], 'original_inventory_sha256': digest(inventory_data),
        'note': 'Execution timestamps, status, configuration, test revisions and review dispositions preserved.'}
    output.write_text(json.dumps(bound, indent=2) + '\n')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True, help='the original inventory used by this execution')
    parser.add_argument('--current', type=Path, help='also require compatibility with this current inventory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fresh', action='store_true', help='producer is attaching metadata to its newly written report')
    args = parser.parse_args()
    print(bind(args.results, args.inventory, args.output, args.current, args.fresh))
