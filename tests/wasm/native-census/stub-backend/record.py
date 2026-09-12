#!/usr/bin/env python3
"""Validate the new registration packet and emit only its unreviewed LL08-a record."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
from check import check

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from reversible import digest, save
TOOLS = HERE.parents[3] / 'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, binding_errors, safe_path


def load_inputs(root):
    names = ['results.json', 'baseline-fasls.json', 'registered-fasls.json', 'restored-fasls.json',
             'baseline-snapshot.json', 'registered-snapshot.json', 'target-results.json', 'unit-controls.json',
             'baseline-tests/test-summary.json', 'registered-tests/test-summary.json']
    names += ['target-sessions/' + mode + '.json' for mode in
              ['clean-1', 'clean-2', 'late-package', 'host-features', 'host-backend',
               'wrong-args', 'wrong-width', 'cached-host-macro', 'dirty-features']]
    return {name: json.loads((root / name).read_text()) for name in names}


def validate(data):
    r = data['results.json']
    if r['execution_status'] != 'PASS' or r['source_revision'] != 'c994217adc56b3f8a564526cee4695893ac84d86':
        raise ValueError('registration run did not pass at U1')
    if r['test_revision'] != '561ab1be82fefd53a61089eaad4357023e1fa961' or r['inputs']['pins']['test_revision'] != r['test_revision']:
        raise ValueError('native test revision differs')
    for key in ('baseline_tests', 'registered_tests'):
        t = r[key]
        if t != data[key.replace('_', '-') + '/test-summary.json']:
            raise ValueError('native summary differs from retained output')
        if not t['success'] or t['eligible'] != 21843 or t['passed'] != 21843 or t['upstream_disabled'] != 75 or any(t[k] for k in ('failed', 'missing', 'unexpected')):
            raise ValueError('native regression incomplete')
    before, after, restored = [data[n + '-fasls.json'] for n in ('baseline', 'registered', 'restored')]
    if len(before) != 164 or before.keys() != after.keys() or restored != before:
        raise ValueError('native FASL inventory/reversal differs')
    if sorted(n for n in before if before[n] != after[n]) != ['bin/systems.dx64fsl']:
        raise ValueError('unexplained native FASL difference')
    if not r['all_archived_sources_restored'] or r['registration_restoration']['active'] or r['restored_fasls_equal'] != 164:
        raise ValueError('complete source/output reversal missing')
    a, b = data['baseline-snapshot.json'], data['registered-snapshot.json']
    if a['snapshot'] != b['snapshot'] or len(a['snapshot']['operators']) != 279 or sum(o['name'] is None for o in a['snapshot']['operators']) != 12:
        raise ValueError('evaluated native operators changed')
    added = {'CCL::WASM-CENSUS-ARCH', 'CCL::WASM-CENSUS-BACKEND'}
    if [m for m in b['modules'] if m['name'] not in added] != a['modules'] or {m['name'] for m in b['modules']} - {m['name'] for m in a['modules']} != added:
        raise ValueError('existing registration changed or added entries missing')
    if data['target-sessions/clean-1.json'] != data['target-sessions/clean-2.json']:
        raise ValueError('clean sessions differ')
    outcomes = data['target-results.json']['outcomes']
    expected = {'clean-1', 'clean-2', 'late-package', 'host-features', 'host-backend', 'wrong-args',
                'wrong-width', 'cached-host-macro', 'dirty-features', 'missing-registration'}
    if {row['mode'] for row in outcomes} != expected or len(outcomes) != len(expected):
        raise ValueError('target-state case/control missing')
    for row in outcomes:
        if row['mode'] == 'missing-registration':
            if row['status'] != 'REJECTED': raise ValueError('registration omission escaped')
            continue
        payload = data['target-sessions/' + row['mode'] + '.json']
        try: count = check(payload)
        except ValueError:
            if row['mode'].startswith('clean-') or row['status'] != 'REJECTED': raise
        else:
            if not row['mode'].startswith('clean-') or row['status'] != 'PASS' or count != 14:
                raise ValueError('semantic control passed or positive case incomplete')
            if any(payload['native_snapshot_after'][k] != v for k, v in a['snapshot'].items()):
                raise ValueError('target session changed native state')
    unit = data['unit-controls.json']
    if unit['status'] != 'PASS' or len(unit['positive_cases']) != 2 or len(unit['controls']) != 6 or any(c['status'] != 'REJECTED' for c in unit['controls']):
        raise ValueError('reversible-unit controls incomplete')
    return {'native_tests_per_variant': 21843, 'native_fasls': 164, 'identical_while_registered': 163,
            'identical_after_removal': 164, 'target_cases': 28, 'target_controls_rejected': 8,
            'unit_controls_rejected': 6, 'operator_slots': 279, 'reserved_slots': 12}


def record(root, inventory_path):
    if (root / 'gate-results.json').exists() or (root / 'sources.tar.gz').exists():
        raise ValueError('never overwrite a produced record')
    data = load_inputs(root); summary = validate(data); run = data['results.json']
    # One scoped verification of this new packet, cached for the envelope. No
    # historical evidence, catalogs or prerequisite trees are scanned.
    hashes = {}; paths = set()
    for a in run['artifacts']:
        name = safe_path(a['path']); path = (root / name).resolve()
        if name in paths or not path.is_relative_to(root) or digest(path) != a['sha256']:
            raise ValueError('changed/escaping/duplicate new artifact: ' + name)
        paths.add(name); hashes[name] = a['sha256']
    hashes['results.json'] = digest(root / 'results.json')
    for label in ('baseline', 'registered'):
        if digest(root / (label + '-probe.dx64fsl')) != hashes['baseline-probe.dx64fsl']:
            raise ValueError('unchanged native probe differs')
    # Check manifest-to-byte joins in the one newly generated baseline archive.
    with tarfile.open(root / 'baseline-fasls.tar.gz') as archive:
        members = archive.getmembers(); names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(data['baseline-fasls.json']):
            raise ValueError('baseline archive member inventory differs')
        for m in members:
            if not m.isfile() or hashlib.sha256(archive.extractfile(m).read()).hexdigest() != data['baseline-fasls.json'][m.name]:
                raise ValueError('baseline member bytes differ')
    if hashes['registered-systems.dx64fsl'] != data['registered-fasls.json']['bin/systems.dx64fsl']:
        raise ValueError('changed registration FASL bytes differ')
    for name, expected in run['fixture_sha256'].items():
        if digest(HERE / safe_path(name)) != expected: raise ValueError('executed fixture source differs: ' + name)
    for name, expected in run['shared_dependencies_sha256'].items():
        if digest(Path(name)) != expected: raise ValueError('executed dependency source differs: ' + name)
    log = (root / 'target-sessions/missing-registration.log').read_text()
    if 'Module WASM-CENSUS-ARCH not defined' not in log: raise ValueError('missing registration failure lacks witness')
    if 'CLEAN-START-PASS' not in (root / 'restored-start.log').read_text(): raise ValueError('clean restart witness absent')
    inventory = json.loads(inventory_path.read_text())
    test = next(t for t in inventory['tests'] if t['id'] == 'S0-LL08-a')
    if test['runner'] != 'tests/wasm/native-census/stub-backend/run.py' or test['variants'] != ['native']:
        raise ValueError('unexpected LL08-a contract')
    shutil.copyfile(inventory_path, root / 'inventory.json')
    # Retain exact executed input sources in one small bundle. Producer/unit
    # controls are later tooling, explicitly separate from the native run inputs.
    sources = {'fixture/' + name: HERE / name for name in run['fixture_sha256']}
    sources.update({'shared/' + Path(name).name: Path(name) for name in run['shared_dependencies_sha256']})
    sources.update({'producer/' + name: HERE / name for name in ('record.py', 'test_record.py', 'test_registration.py')})
    sources['producer/evidence_binding.py'] = TOOLS / 'evidence_binding.py'
    with tarfile.open(root / 'sources.tar.gz', 'w:gz') as archive:
        for name, path in sorted(sources.items()): archive.add(path, arcname=name)
    save(root / 'qualification.json', {**summary, 'scope': run['scope'],
                                     'verification_scope': 'New packet, direct sources, native manifest/member joins and semantic controls only; unchanged evidence reused.'})
    for name in ('inventory.json', 'sources.tar.gz', 'qualification.json', 'unit-controls.json', 'producer-controls.json'):
        hashes[name] = digest(root / name)
    artifacts = []
    for name, h in sorted(hashes.items()):
        role = ('schema' if name in ('inventory.json', 'patch.json') else
                'test' if name in ('sources.tar.gz', 'unit-controls.json', 'producer-controls.json') else
                'implementation' if not name.startswith('development-failures/') and
                 (name.endswith(('.dx64fsl', '.tar.gz', '.patch'))) else 'log')
        artifacts.append({'path': name, 'role': role, 'sha256': h})
    result = {'id': test['id'], 'variant': 'native', 'status': 'PASS', 'source_revision': run['source_revision'],
              'evidence_kind': test['evidence_kind'], 'test_revision': hashes['sources.tar.gz'],
              'timestamp': run['completed_utc'], 'command': 'tests/wasm/native-census/stub-backend/run.py; exact commands and environment in commands.json',
              'toolchain': {'host': (root / 'host.log').read_text(), 'compiler': (root / 'compiler.log').read_text(), 'kernel_sha256': run['inputs']['kernel_sha256']},
              'engine': 'CCL U1 v1.13 / macOS x86-64', 'seed': 100000,
              'configuration': {**summary, 'scope': run['scope'], 'normalizations': [],
                                'loading_recipe': 'Compile/load the registered architecture, then backend, in a fresh native session; bind backend, features, FASL target, foreign data and TARGET/OS nicknames before target-dependent source is read.',
                                'scope_exclusions': run['skips'], 'native_disabled_tests': '75 upstream-disabled cases disclosed in both test inventories.',
                                'full_census': 'NOT_CLAIMED; the static acode/dependency records cover this fourteen-form source corpus.'},
              'substitutions': [], 'skips': [], 'review_disposition': 'NOT_REVIEWED',
              'assertions': [{'id': a['id'], 'status': 'PASS'} for a in test['assertions']], 'artifacts': artifacts}
    base = {'version': 1, 'source_revision': run['source_revision'], 'inventory_sha256': hashes['inventory.json'], 'results': [result]}
    envelope = bind_report(base, inventory, 'inventory.json', hashes['inventory.json'])
    errors = binding_errors(inventory, envelope, lambda n: (root / n).read_bytes())
    if errors: raise ValueError('; '.join(errors))
    save(root / 'gate-results.json', envelope)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path); p.add_argument('--inventory', required=True, type=Path)
    a = p.parse_args(); print(json.dumps(record(a.run.resolve(), a.inventory.resolve()), indent=2))
