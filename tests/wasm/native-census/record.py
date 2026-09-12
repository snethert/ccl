#!/usr/bin/env python3
"""Verify a completed observation run and emit only the native LL08-b record."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from analyze import analyze
from reversible import digest, save

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[2] / 'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, safe_path


def record(root, inventory_path):
    result_path = root / 'gate-results.json'
    if result_path.exists() or (root / 'producer').exists():
        raise ValueError('never overwrite retained evidence')
    report = json.loads((root / 'results.json').read_text())
    inventory = json.loads(inventory_path.read_text())
    if report['source_revision'] != inventory['source_revision']:
        raise ValueError('source revision differs from inventory')
    seen = set()
    for a in report['artifacts']:
        name = safe_path(a['path']); p = (root / name).resolve()
        if name in seen or not p.is_relative_to(root) or digest(p) != a['sha256']:
            raise ValueError('missing, repeated, escaping or changed artifact: ' + name)
        seen.add(name)
    for n in ['observer.lisp', 'observation.patch', 'patch.json', 'probe.lisp', 'run.py', 'reversible.py']:
        if 'runner/' + n not in seen or digest(root / 'runner' / n) != digest(HERE / n):
            raise ValueError('executed harness differs from this producer: ' + n)
    for label in ['baseline', 'observed']:
        s = report[label + '_tests']
        if not s['success'] or s['passed'] != s['eligible'] or s['eligible'] != 21843 or any(
                s[k] for k in ['failed', 'missing', 'unexpected']):
            raise ValueError('native regression run incomplete')
    builds = [json.loads((root / label / 'fasls.json').read_text())
              for label in ['baseline', 'observed', 'restored-clean']]
    baseline, observed, restored = builds
    if len(baseline) != 164 or baseline.keys() != observed.keys() or restored != baseline:
        raise ValueError('native FASL inventory or clean rebuild differs')
    changed = sorted(n for n in baseline if baseline[n] != observed[n])
    if changed != ['bin/dumplisp.dx64fsl', 'bin/nfcomp.dx64fsl', 'l1-fasls/nx.dx64fsl']:
        raise ValueError('unexplained or missing shared artifact differences')
    for label, hashes in zip(['baseline', 'observed', 'restored-clean'], builds):
        for n, h in hashes.items():
            name = label + '/build/' + n
            if name not in seen or digest(root / name) != h:
                raise ValueError('FASL manifest differs from retained bytes')
    if digest(root / 'baseline-probe.dx64fsl') != digest(root / 'observed-probe.dx64fsl'):
        raise ValueError('unchanged probe FASL differs')
    if report.get('clean_output_restoration') != {
        'status': 'PASS', 'files': 167,
        'source': 'unmodified native baseline; observed artifacts are evidence only'}:
        raise ValueError('complete clean output restoration missing')
    analysis = analyze(root)
    if (analysis['operator_slots'], analysis['reserved_slots']) != (279, 12):
        raise ValueError('U1 evaluated slot inventory differs')
    test = next(t for t in inventory['tests'] if t['id'] == 'S0-LL08-b')
    if test['variants'] != ['native'] or test['runner'] != 'tests/wasm/native-census/run.py':
        raise ValueError('unexpected LL08-b contract')
    producer = root / 'producer'; producer.mkdir()
    for name in ['record.py', 'analyze.py', 'reversible.py']:
        shutil.copyfile(HERE / name, producer / name)
    shutil.copyfile(TOOLS / 'evidence_binding.py', producer / 'evidence_binding.py')
    shutil.copyfile(inventory_path, root / 'inventory.json')
    save(root / 'analysis.json', analysis)
    artifacts = []
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel = p.relative_to(root).as_posix()
        role = ('schema' if rel in ['inventory.json', 'pins.json', 'runner/patch.json'] else
                'implementation' if p.suffix in ['.image', '.dx64fsl'] or p.name in ['observer.lisp', 'observation.patch', 'dx86cl64'] else
                'test' if rel.startswith(('runner/', 'producer/')) else 'log')
        artifacts.append({'path': rel, 'role': role, 'sha256': digest(p)})
    result = {'id': test['id'], 'variant': 'native', 'status': 'PASS',
        'source_revision': report['source_revision'], 'evidence_kind': test['evidence_kind'],
        'test_revision': digest(root / 'runner/patch.json'), 'timestamp': report['completed_utc'],
        'command': 'tests/wasm/native-census/run.py; exact commands/environment retained in commands.json',
        'toolchain': {n: (root / (n + '.log')).read_text() for n in ['compiler', 'sdk', 'os', 'm4']},
        'engine': 'CCL U1 v1.13 / macOS x86-64', 'seed': 100000,
        'configuration': {'scope': 'Evaluated acode IDs, flags and reserved slots under R6a',
            'comparison_inputs': report['comparison_inputs'], 'normalizations': [],
            'native_tests': report['baseline_tests'], 'disabled_test_names_and_notes':
            'baseline-tests/test-inventory.sexp and observed-tests/test-inventory.sexp',
            'operator_slots': 279, 'reserved_slots': 12,
            'census_scope': 'LL15-b/c remains blocked; this record does not claim trace/closure completion'},
        'substitutions': [], 'skips': [], 'review_disposition': 'NOT_REVIEWED',
        'assertions': [{'id': a['id'], 'status': 'PASS'} for a in test['assertions']],
        'artifacts': artifacts}
    envelope = {'version': 1, 'source_revision': report['source_revision'],
                'inventory_sha256': digest(inventory_path), 'results': [result]}
    save(result_path, bind_report(envelope, inventory, 'inventory.json', digest(inventory_path)))
    return result_path


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True); p.add_argument('--inventory', type=Path, required=True)
    a = p.parse_args(); print(record(a.run.resolve(), a.inventory.resolve()))
