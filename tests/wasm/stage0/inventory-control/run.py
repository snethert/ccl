#!/usr/bin/env python3
"""Execute S0-LL02-a against the production gate CLI; retain every test input."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOOLS = ROOT/'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash

ID = 'S0-LL02-a'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value): p.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def read(p): return json.loads(p.read_text())


def fixture(out, cases, revision):
    q = out/'quarantine'; q.mkdir()
    # ACCEPTED inside these CONTROL-* inputs is a deliberate checker input,
    # not an acceptance of any project record. All live S0 IDs stay outside it.
    (q/'fixture.txt').write_text('Synthetic validator input only; no CCL, Wasm, build, review or project acceptance claim.\n')
    roles = ['implementation', 'test', 'schema', 'log']
    inventory = dict(version=1, source_revision=revision, required_record_roles=roles,
                     stage='QUARANTINED_SYNTHETIC_GATE_INPUTS', tests=[dict(
                       id=t['id'], variants=t['variants'], source_revision=revision,
                       evidence_kind='CONTROL EXECUTION', runner='synthetic-input-only',
                       prerequisites=[], assertions=[dict(id=t['id']+':assertion', description='synthetic checker input')])
                       for t in cases['required_tests']])
    save(q/'inventory.json', inventory)
    records = [dict(id=t['id'], variant=v, source_revision=revision, evidence_kind='CONTROL EXECUTION',
                    status='PASS', assertions=[dict(id=t['id']+':assertion', status='PASS')],
                    artifacts=[dict(role=r, path='fixture.txt', sha256=sha(q/'fixture.txt')) for r in roles],
                    substitutions=[], skips=[], review_disposition='ACCEPTED',
                    review_record='Synthetic acceptance flag for the checker control only; no project review.',
                    **{k: 'SYNTHETIC CHECKER INPUT, NOT EXECUTION' for k in
                       ['command', 'toolchain', 'engine', 'timestamp', 'configuration', 'seed', 'test_revision']})
               for t in cases['required_tests'] for v in t['variants']]
    complete = bind_report(dict(version=1, source_revision=revision,
                                inventory_sha256=sha(q/'inventory.json'), results=records),
                           inventory, 'inventory.json', sha(q/'inventory.json'))
    for case in cases['cases']:
        report = copy.deepcopy(complete); rows = report['results']; kind = case['mutation']
        if kind == 'none': pass
        elif kind == 'reverse': rows.reverse()
        elif kind == 'omit-id': report['results'] = [r for r in rows if r['id'] != case['id']]
        elif kind == 'omit-pair': report['results'] = [r for r in rows if (r['id'], r['variant']) != (case['id'], case['variant'])]
        elif kind == 'wrong-variant': rows[-1]['variant'] = 'unrequested'
        elif kind == 'duplicate': rows[-1] = copy.deepcopy(rows[0])
        elif kind == 'empty': report['results'] = []
        else: raise ValueError('unknown mutation: '+kind)
        save(q/(case['name']+'.json'), report)


def exercise(out, cases):
    observations = []
    for case in cases['cases']:
        argv = [sys.executable, str(TOOLS/'gate.py'), '--inventory', str(out/'quarantine/inventory.json'),
                '--results', str(out/'quarantine'/(case['name']+'.json'))]
        try:
            p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15)
            observation = dict(case=case['name'], command=argv, exit_code=p.returncode,
                               stdout=p.stdout, stderr=p.stderr, expected=case['expected'])
        except subprocess.TimeoutExpired as e:
            save(out/'commands.json', observations+[dict(case=case['name'], command=argv, error='TIMEOUT',
                                                        stdout=str(e.stdout), stderr=str(e.stderr))])
            raise
        observations.append(observation); save(out/'commands.json', observations)
        expected_code = {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[case['expected']['status']]
        if p.returncode != expected_code or p.stderr or json.loads(p.stdout) != case['expected']:
            raise ValueError('production gate returned an unexpected result: '+case['name'])
    return [dict(case=r['case'], exit_code=r['exit_code'], result=json.loads(r['stdout'])) for r in observations]


def verify(packet):
    record = read(packet/'run.json')
    for p, expected in record['source_sha256'].items():
        if sha(ROOT/p) != expected: raise ValueError('executed source differs: '+p)
    cases = read(packet/'cases.json')
    # Execute the retained inputs without rebuilding them or modifying the packet.
    for case in cases['cases']:
        p = subprocess.run([sys.executable, str(TOOLS/'gate.py'), '--inventory', str(packet/'quarantine/inventory.json'),
                            '--results', str(packet/'quarantine'/(case['name']+'.json'))],
                           cwd=ROOT, capture_output=True, text=True, timeout=15)
        if p.returncode != {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[case['expected']['status']] or p.stderr or json.loads(p.stdout) != case['expected']:
            raise ValueError('retained control differs: '+case['name'])
    print('PASS: two complete inventories accepted by the production gate; seven defective inventories rejected.')


def run(out):
    if out == ROOT or ROOT in out.parents: raise ValueError('use a new output directory outside the checkout')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', command=sys.argv, timestamp=datetime.now(timezone.utc).isoformat())
    try:
        inventory_path = ROOT/'doc/WASM/stage0/inventory.json'; inventory = read(inventory_path)
        test = next(t for t in inventory['tests'] if t['id'] == ID)
        if test['runner'] != str(HERE.relative_to(ROOT)/'run.py') or test['variants'] != ['control']:
            raise ValueError('runner not registered for the required contract')
        sources = [HERE/'run.py', HERE/'cases.json', TOOLS/'gate.py', TOOLS/'evidence_binding.py']
        record['source_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in sources}
        (out/'source').mkdir()
        for p in sources: (out/'source'/p.name).write_bytes(p.read_bytes())
        (out/'inventory.json').write_bytes(inventory_path.read_bytes())
        cases = read(HERE/'cases.json'); save(out/'cases.json', cases)
        if cases['test_id'] != ID: raise ValueError('wrong test contract')
        fixture(out, cases, inventory['source_revision'])
        results = exercise(out, cases)
        summary = dict(version=1, id=ID, variant='control', status='PASS', review_disposition='NOT_REVIEWED',
                       scope=cases['scope'], positive_cases=2, rejection_cases=7, cases=results)
        save(out/'summary.json', summary)
        environment = dict(python=sys.version, executable=sys.executable,
                           executable_sha256=sha(Path(sys.executable).resolve()), platform=platform.platform())
        save(out/'environment.json', environment)
        save(out/'observations.json', results)
        artifacts = [dict(path=str(p.relative_to(out)), sha256=sha(p), role=(
                       'implementation' if p.name in ('gate.py', 'evidence_binding.py') else
                       'test' if p.name == 'run.py' else
                       'schema' if p.name in ('cases.json', 'inventory.json') else 'log'))
                     for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'run.json']
        report = dict(version=1, source_revision=inventory['source_revision'], inventory_sha256=sha(out/'inventory.json'),
                      scope='Actual production-gate control execution, not compiler/runtime evidence.', results=[dict(
                        id=ID, variant='control', source_revision=test['source_revision'], evidence_kind=test['evidence_kind'],
                        status='PASS', assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']],
                        artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
                        command=[sys.executable, *sys.argv], toolchain=environment, engine='Python production gate CLI',
                        timestamp=record['timestamp'], configuration=cases['scope'], seed='deterministic named omissions',
                        test_revision=record['source_sha256'][str((HERE/'run.py').relative_to(ROOT))])])
        save(out/'results.json', bind_report(report, inventory, 'inventory.json', sha(out/'inventory.json')))
        # Scope validation to this real slot. No synthetic acceptance of it.
        subset = copy.deepcopy(inventory); subset['tests'] = [test]; save(out/'slot-inventory.json', subset)
        p = subprocess.run([sys.executable, str(TOOLS/'gate.py'), '--inventory', str(out/'slot-inventory.json'),
                            '--results', str(out/'results.json')], cwd=ROOT, capture_output=True, text=True, timeout=15)
        save(out/'slot-gate.json', dict(exit_code=p.returncode, result=json.loads(p.stdout), stderr=p.stderr))
        if p.returncode != 2 or p.stderr or json.loads(p.stdout) != dict(status='BLOCKED', reasons=['unreviewed S0-LL02-a [control]']):
            raise ValueError('real result fails slot validation')
        record.update(status='PASS', contract_sha256=contract_hash(inventory, ID))
        print('PASS: S0-LL02-a; two positive cases, seven rejected controls. Slot gate BLOCKED only for independent review/acceptance.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e); raise
    finally: save(out/'run.json', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path); group.add_argument('--verify', type=Path)
    a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
