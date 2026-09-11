#!/usr/bin/env python3
"""Verify retained pack identities and reject a stale inventory labeled CURRENT."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from evidence_binding import binding_errors, safe_path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(include_external=False):
    index = json.loads((ROOT / 'evidence/index.json').read_text())
    inventory_hash = digest(ROOT / 'stage0/inventory.json')
    checked = 0
    for record in index['current_runs']:
        external = 'path' not in record
        if external and not include_external:
            continue
        path = Path(record['locator']) if external else ROOT / record['path']
        if not path.is_file() or digest(path) != record['sha256']:
            raise ValueError('missing or mismatched retained evidence: ' + record['id'])
        if record.get('currency') == 'CURRENT':
            def verify(report, read_bytes):
                if type(report.get('version')) is not int or report['version'] not in (1, 2):
                    raise ValueError('unsupported CURRENT evidence envelope: ' + record['id'])
                if record.get('inventory_sha256') != report.get('inventory_sha256'):
                    raise ValueError('index and original inventory provenance disagree: ' + record['id'])
                if report.get('version') == 2:
                    current = json.loads((ROOT / 'stage0/inventory.json').read_text())
                    errors = binding_errors(current, report, read_bytes)
                    if errors:
                        raise ValueError('CURRENT contract binding failed: ' + record['id'] + ': ' + '; '.join(errors))
                elif record.get('inventory_sha256') != inventory_hash:
                    raise ValueError('legacy CURRENT evidence uses a superseded inventory: ' + record['id'])
            if path.suffix == '.zip':
                with ZipFile(path) as archive:
                    verify(json.loads(archive.read(record['results_member'])), lambda name: archive.read(safe_path(name)))
            else:
                def local(name):
                    p = (path.parent / safe_path(name)).resolve()
                    if not p.is_relative_to(path.parent.resolve()):
                        raise ValueError('escaping inventory snapshot')
                    return p.read_bytes()
                verify(json.loads(path.read_text()), local)
        checked += 1
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-external', action='store_true', help='require and verify local external-store packs too')
    args = parser.parse_args()
    print(f'PASS: {check(args.include_external)} retained evidence identities; CURRENT inventory bindings match.')
