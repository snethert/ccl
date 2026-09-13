#!/usr/bin/env python3
"""S0-LL03-a: execute evidence-kind controls against the unchanged production gate."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOOLS = ROOT/'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash

ID = 'S0-LL03-a'
KINDS = {'generated': 'COMPILER-GENERATED TARGET EXECUTION',
         'hand': 'HAND-BUILT WASM EXECUTION', 'synthetic': 'CONTROL EXECUTION'}
VARIANTS = ['full:C', 'full:C4', 'full:B', 'reduced:C', 'reduced:C4', 'reduced:B']
ROLES = ['implementation', 'test', 'schema', 'log']
LABEL_FIELDS = ['id', 'variant', 'evidence_kind', 'configuration', 'substitutions', 'skips', 'artifacts']


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, value): p.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def require(ok, why):
    if not ok: raise ValueError(why)


def source_paths():
    return [HERE/'run.py', HERE/'cases.json', TOOLS/'gate.py', TOOLS/'evidence_binding.py']


def fixture(q, revision):
    q.mkdir()
    (q/'payload').mkdir()
    # All inputs, including generated-shaped positive controls, are synthetic.
    # A PASS here tests metadata validation, not the asserted production origin.
    inventory = dict(version=1, stage='QUARANTINED_SYNTHETIC_GATE_INPUTS', source_revision=revision,
        required_record_roles=ROLES, tests=[dict(id='CONTROL-'+kind, variants=VARIANTS,
            source_revision=revision, evidence_kind=label, runner='synthetic-input-only', prerequisites=[],
            assertions=[dict(id='CONTROL-'+kind+':assertion', description='Synthetic checker input only')])
            for kind, label in KINDS.items()])
    save(q/'inventory.json', inventory)
    records = []
    for kind, label in KINDS.items():
        for variant in VARIANTS:
            profile, candidate = variant.split(':')
            payload = q/'payload'/(kind+'-'+profile+'-'+candidate+'.txt')
            payload.write_text('SYNTHETIC CHECKER INPUT; no compiler, Wasm or Lisp execution.\n'
                               f'Declared class: {label}; profile: {profile}; candidate: {candidate}.\n')
            records.append(dict(id='CONTROL-'+kind, variant=variant, source_revision=revision,
                evidence_kind=label, status='PASS', assertions=[dict(id='CONTROL-'+kind+':assertion', status='PASS')],
                configuration=dict(candidate=candidate, profile=profile, fixture_id=payload.stem,
                                   actual_input_origin='SYNTHETIC CHECKER INPUT'),
                artifacts=[dict(role=role, path=str(payload.relative_to(q)), sha256=sha(payload)) for role in ROLES],
                substitutions=[], skips=[], review_disposition='ACCEPTED',
                review_record='Synthetic checker flag; no project review or acceptance.',
                **{k:'SYNTHETIC CHECKER INPUT, NOT PRODUCTION EXECUTION' for k in
                   ('command', 'toolchain', 'engine', 'timestamp', 'seed', 'test_revision')}))
    return bind_report(dict(version=1, source_revision=revision, inventory_sha256=sha(q/'inventory.json'),
                            results=records), inventory, 'inventory.json', sha(q/'inventory.json'))


def mutate(base, case):
    report = copy.deepcopy(base)
    rows = report['results']
    if case['mutation'] == 'none': return report, None
    if case['mutation'] == 'reverse': rows.reverse(); return report, None
    index = next(i for i, r in enumerate(rows) if (r['id'], r['variant']) == (case['id'], case['variant']))
    row = rows[index]
    if case['mutation'] == 'kind':
        # Offer the other class's complete labelled payload under the generated
        # requirement. Change only its claimed requirement/assertion/binding;
        # preserve the actual declared kind, configuration and artifact identity.
        incoming = copy.deepcopy(next(r for r in rows if r['id'] == case['source_id'] and r['variant'] == case['variant']))
        incoming.update({k:copy.deepcopy(row[k]) for k in ('id', 'assertions', 'contract_binding')})
        rows[index] = row = incoming
    elif case['mutation'] == 'substitution': row['substitutions'] = [dict(import_name='required-entry', replacement='synthetic-return-zero')]
    elif case['mutation'] == 'omit-substitutions': del row['substitutions']
    elif case['mutation'] == 'skip': row['skips'] = ['required target execution unavailable']
    elif case['mutation'] == 'status': row['status'] = case['value']
    elif case['mutation'] == 'unreviewed': row['review_disposition'] = 'NOT_REVIEWED'
    elif case['mutation'] == 'artifact': row['artifacts'][0]['sha256'] = '0'*64
    elif case['mutation'] == 'replace-variant':
        row = copy.deepcopy(next(r for r in rows if r['id'] == case['id'] and r['variant'] == case['replacement']))
        rows[index] = row
    else: raise ValueError('unknown control mutation: '+case['mutation'])
    if case['mutation'] in ('status', 'unreviewed'):
        require({k:row[k] for k in LABEL_FIELDS} == {k:base['results'][index][k] for k in LABEL_FIELDS}, 'STATUS_CHANGED_LABELS')
    return report, dict(status=row['status'], **{k:row.get(k) for k in LABEL_FIELDS})


def invoke(inventory, report):
    argv = [sys.executable, str(TOOLS/'gate.py'), '--inventory', str(inventory), '--results', str(report)]
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15)
    return dict(command=argv, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)


def expected(observation, case):
    require(observation['exit_code'] == {'PASS':0, 'FAIL':1, 'BLOCKED':2}[case['expected']['status']]
            and observation['stderr'] == '' and json.loads(observation['stdout']) == case['expected'],
            'UNEXPECTED_GATE_RESULT '+case['name'])


def exercise(out, cases, base):
    commands, observations = [], []
    for case in cases['cases']:
        report, subject = mutate(base, case)
        path = out/'quarantine'/(case['name']+'.json'); save(path, report)
        try: result = invoke(out/'quarantine/inventory.json', path)
        except subprocess.TimeoutExpired as e:
            save(out/'commands.json', commands+[dict(case=case['name'], error='TIMEOUT',
                 command=e.cmd, stdout=str(e.stdout), stderr=str(e.stderr))]); raise
        commands.append(dict(case=case['name'], **result)); save(out/'commands.json', commands)
        expected(result, case)
        observations.append(dict(case=case['name'], exit_code=result['exit_code'],
                                 result=json.loads(result['stdout']), subject=subject))
    save(out/'observations.json', observations)
    return observations


def slot_gate(out):
    inventory = read(out/'inventory.json')
    subset = copy.deepcopy(inventory); subset['tests'] = [t for t in inventory['tests'] if t['id'] == ID]
    save(out/'slot-inventory.json', subset)
    result = invoke(out/'slot-inventory.json', out/'results.json')
    save(out/'slot-gate.json', dict(exit_code=result['exit_code'], result=json.loads(result['stdout']), stderr=result['stderr']))
    expected(result, dict(name='real slot', expected=dict(status='BLOCKED', reasons=['unreviewed S0-LL03-a [control]'])))


def run(out):
    require(out != ROOT and ROOT not in out.parents, 'USE_FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv],
                  timestamp=datetime.now(timezone.utc).isoformat(),
                  source_sha256={str(p.relative_to(ROOT)):sha(p) for p in source_paths()})
    try:
        inventory_path = ROOT/'doc/WASM/stage0/inventory.json'; inventory = read(inventory_path)
        test = next(t for t in inventory['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT)/'run.py') and test['variants'] == ['control'], 'UNREGISTERED_RUNNER')
        (out/'source').mkdir()
        for p in source_paths(): (out/'source'/p.name).write_bytes(p.read_bytes())
        (out/'inventory.json').write_bytes(inventory_path.read_bytes())
        cases = read(HERE/'cases.json'); save(out/'cases.json', cases)
        require(cases['test_id'] == ID and len(cases['cases']) == 24 and
                len({c['name'] for c in cases['cases']}) == 24, 'CASE_BOUND')
        base = fixture(out/'quarantine', inventory['source_revision'])
        observations = exercise(out, cases, base)
        counts = {s:sum(r['result']['status'] == s for r in observations) for s in ('PASS', 'FAIL', 'BLOCKED')}
        require(counts == dict(PASS=2, FAIL=21, BLOCKED=1), 'RESULT_COUNTS')
        save(out/'summary.json', dict(version=1, id=ID, variant='control', status='PASS',
            review_disposition='NOT_REVIEWED', scope=cases['scope'], synthetic_input_records=18,
            candidate_profiles=VARIANTS, positive_cases=2, rejected_cases=22, case_status_counts=counts,
            metadata_preserved_on_failure=True, production_compiler_or_wasm_execution=False))
        environment = dict(python=sys.version, executable=sys.executable,
            executable_sha256=sha(Path(sys.executable).resolve()), platform=platform.platform())
        save(out/'environment.json', environment)
        artifacts = [dict(path=str(p.relative_to(out)), sha256=sha(p), role=(
            'implementation' if p.name in ('gate.py', 'evidence_binding.py') else
            'test' if p.name == 'run.py' else 'schema' if p.name in ('cases.json', 'inventory.json') else 'log'))
            for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'run.json']
        report = dict(version=1, source_revision=inventory['source_revision'], inventory_sha256=sha(out/'inventory.json'),
            scope='Actual evidence-kind production-gate control execution; all inner records are quarantined synthetic inputs.',
            results=[dict(id=ID, variant='control', source_revision=test['source_revision'], evidence_kind=test['evidence_kind'],
                status='PASS', assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']],
                artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
                command=record['command'], toolchain=environment, engine='Python production gate CLI',
                timestamp=record['timestamp'], configuration=cases['scope'], seed='deterministic named evidence-kind controls',
                test_revision=record['source_sha256'][str((HERE/'run.py').relative_to(ROOT))])])
        save(out/'results.json', bind_report(report, inventory, 'inventory.json', sha(out/'inventory.json')))
        slot_gate(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)):sha(p) for p in source_paths()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inventory, ID))
        print('PASS: S0-LL03-a; 2 positive inputs, 22 rejected controls. Real slot blocked only for review/acceptance.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e); raise
    finally: save(out/'run.json', record)


def verify(packet):
    record = read(packet/'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, digest in record['source_sha256'].items(): require(sha(ROOT/name) == digest, 'SOURCE_PIN '+name)
    cases = read(packet/'cases.json'); require(cases == read(HERE/'cases.json'), 'CASE_SOURCE')
    base = read(packet/'quarantine/complete.json')
    with tempfile.TemporaryDirectory(prefix='ccl-kind-verification-') as tmp:
        q = Path(tmp)/'quarantine'
        rebuilt = fixture(q, read(packet/'inventory.json')['source_revision'])
        require(rebuilt == base and read(q/'inventory.json') == read(packet/'quarantine/inventory.json'), 'FIXTURE_BASE')
    # Reconstruct each declared mutation from the retained positive input, then
    # independently execute the production CLI on the unchanged retained bytes.
    observed = []
    for case in cases['cases']:
        report, subject = mutate(base, case)
        require(report == read(packet/'quarantine'/(case['name']+'.json')), 'RETAINED_CASE '+case['name'])
        result = invoke(packet/'quarantine/inventory.json', packet/'quarantine'/(case['name']+'.json'))
        expected(result, case)
        observed.append(dict(case=case['name'], exit_code=result['exit_code'], result=json.loads(result['stdout']), subject=subject))
    require(observed == read(packet/'observations.json'), 'OBSERVATIONS')
    result = invoke(packet/'slot-inventory.json', packet/'results.json')
    expected(result, dict(name='retained real slot', expected=dict(status='BLOCKED', reasons=['unreviewed S0-LL03-a [control]'])))
    print('PASS: retained 24 production-gate cases, exact classifications/artifacts, source pins and real-slot envelope.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path)
    a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
