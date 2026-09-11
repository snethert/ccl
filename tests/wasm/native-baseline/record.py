#!/usr/bin/env python3
"""Verify a completed native run and bind it to the current Gate 0 inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(root, inventory_path):
    result_path = root / 'gate-results.json'
    if result_path.exists():
        raise ValueError('never overwrite a retained gate record')
    report = json.loads((root / 'results.json').read_text())
    inventory = json.loads(inventory_path.read_text())
    if report['execution_status'] != 'PASS' or len(report['runs']) != 2:
        raise ValueError('native run did not complete two successful builds and test runs')
    if report['source_revision'] != inventory['source_revision']:
        raise ValueError('native source revision differs from inventory')
    if report['source_preservation'] != 'ALL_ARCHIVED_SOURCE_FILES_UNCHANGED':
        raise ValueError('native source preservation was not verified')
    for artifact in report['artifacts']:
        p = (root / artifact['path']).resolve()
        if not p.is_relative_to(root.resolve()) or digest(p) != artifact['sha256']:
            raise ValueError('native artifact mismatch: ' + artifact['path'])
    for run in report['runs']:
        stats = run['tests']
        if not stats['success'] or stats['passed'] != stats['eligible'] or stats['failed'] or stats['missing'] or stats['unexpected']:
            raise ValueError('incomplete native test corpus: ' + run['id'])
    gate0 = next(t for t in inventory['tests'] if t['id'] == 'G0-U1-a')
    if gate0['variants'] != ['macos-x86-64']:
        raise ValueError('wrong native reference variant')
    shutil.copy2(inventory_path, root / 'inventory.json')
    (root / 'producer').mkdir()
    shutil.copy2(__file__, root / 'producer/record.py')
    artifacts = []
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        role = ('schema' if rel in ('pins.json', 'inventory.json') else
                'test' if rel.startswith(('runner/', 'producer/')) else
                'implementation' if p.suffix in ('.dx64fsl', '.image') or p.name == 'dx86cl64' else 'log')
        artifacts.append({'path': rel, 'sha256': digest(p), 'role': role})
    result = {'id': 'G0-U1-a', 'variant': 'macos-x86-64', 'status': 'PASS',
              'source_revision': report['source_revision'], 'evidence_kind': 'NATIVE BASELINE EXECUTION',
              'test_revision': report['test_revision'], 'timestamp': report['completed_utc'],
              'command': 'tests/wasm/native-baseline/run.py; exact argv, cwd and environment in commands.json',
              'toolchain': {n: (root / (n + '.log')).read_text() for n in ['compiler', 'linker', 'sdk', 'macos', 'm4', 'make']},
              'engine': 'CCL v1.13 / macOS x86-64', 'seed': 0,
              'configuration': {'builds': 2, 'test_scope': 'upstream eligible corpus, frozen before each run',
                                'upstream_disabled': [r['tests']['upstream_disabled'] for r in report['runs']],
                                'disabled_test_names_and_notes': 'run-1/test-inventory.sexp and run-2/test-inventory.sexp',
                                'repeatability': report['repeatability']},
              'substitutions': [], 'skips': [], 'review_disposition': 'NOT_REVIEWED',
              'assertions': [{'id': a['id'], 'status': 'PASS'} for a in gate0['assertions']], 'artifacts': artifacts}
    result_path.write_text(json.dumps({'version': 1, 'source_revision': report['source_revision'],
                                     'inventory_sha256': digest(inventory_path), 'results': [result]}, indent=2) + '\n')
    return result_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    args = parser.parse_args()
    print(record(args.run.resolve(), args.inventory.resolve()))
