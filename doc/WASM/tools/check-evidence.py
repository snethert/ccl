#!/usr/bin/env python3
"""Verify retained pack identities and reject a stale inventory labeled CURRENT."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

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
        if record.get('currency') == 'CURRENT' and record.get('inventory_sha256'):
            if record['inventory_sha256'] != inventory_hash:
                raise ValueError('CURRENT evidence uses a superseded inventory: ' + record['id'])
            if path.suffix == '.zip':
                with ZipFile(path) as archive:
                    report = json.loads(archive.read(record['results_member']))
            else:
                report = json.loads(path.read_text())
            if report['inventory_sha256'] != inventory_hash:
                raise ValueError('CURRENT result envelope uses a superseded inventory: ' + record['id'])
        checked += 1
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-external', action='store_true', help='require and verify local external-store packs too')
    args = parser.parse_args()
    print(f'PASS: {check(args.include_external)} retained evidence identities; CURRENT inventory bindings match.')
