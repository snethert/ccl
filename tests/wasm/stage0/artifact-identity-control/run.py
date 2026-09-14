#!/usr/bin/env python3
"""S0-LL22-a: run artifact identity controls through the unchanged production gate."""
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

ID = 'S0-LL22-a'
SUBJECT = 'CONTROL-ARTIFACT-IDENTITY'
REVISION = 'SYNTHETIC-IDENTITY-CONTROL-NOT-U1'
FACETS = {'source': 'input.lisp', 'implementation': 'implementation.c', 'test': 'test.py',
          'abi': 'abi.json', 'template': 'template.wat', 'installed-binary': 'module.wasm',
          'image': 'image.bin', 'host-compiler': 'compiler.txt', 'options': 'options.json', 'log': 'execution.log'}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, value): p.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def require(ok, why):
    if not ok: raise ValueError(why)


def source_paths(): return [HERE/'run.py', HERE/'cases.json', TOOLS/'gate.py', TOOLS/'evidence_binding.py']


def fixture(q):
    q.mkdir()
    (q/'SCOPE.txt').write_text('QUARANTINED SYNTHETIC CHECKER INPUTS. No compiler, image, or Wasm execution.\n')
    inventory = dict(version=1, stage='QUARANTINED_SYNTHETIC_IDENTITY_INPUTS', source_revision=REVISION,
        required_record_roles=list(FACETS), tests=[dict(id=SUBJECT, variants=['synthetic'],
            source_revision=REVISION, evidence_kind='CONTROL EXECUTION', runner='synthetic-input-only',
            prerequisites=[], assertions=[dict(id=SUBJECT+':hashes', description='Every declared artifact has retained bytes')])])
    save(q/'inventory.json', inventory)
    reports = {}
    for cohort, value in [('a', 7), ('b', 9)]:
        bundle = q/('build-'+cohort); bundle.mkdir()
        for role, filename in FACETS.items():
            data = f'SYNTHETIC CHECKER INPUT; no execution. Facet={role}; cohort={cohort}.\n'.encode('ascii')
            if role == 'template':
                data = b';; SYNTHETIC TEMPLATE; not run through a materializer.\n(module (func (export "value") (result i32) i32.const @VALUE@))\n'
            elif role == 'installed-binary':
                # Two hand-encoded modules, deliberately never instantiated.
                # Identical template bytes cannot identify both installed bytes.
                data = bytes.fromhex('0061736d010000000105016000017f030201000709010576616c756500000a0601040041')+bytes([value, 11])
            elif role in ('abi', 'options'):
                data = (json.dumps(dict(scope='SYNTHETIC CHECKER INPUT', facet=role, cohort=cohort, value=value), sort_keys=True)+'\n').encode()
            (bundle/filename).write_bytes(data)
        row = dict(id=SUBJECT, variant='synthetic', source_revision=REVISION, evidence_kind='CONTROL EXECUTION',
            status='PASS', assertions=[dict(id=SUBJECT+':hashes', status='PASS')],
            artifacts=[dict(role=role, path=f'build-{cohort}/{filename}', sha256=sha(bundle/filename)) for role, filename in FACETS.items()],
            substitutions=[], skips=[], review_disposition='ACCEPTED',
            review_record='Synthetic input flag; not a project acceptance.',
            configuration=dict(cohort=cohort, scope='SYNTHETIC CHECKER INPUT; no execution'),
            test_revision=sha(bundle/FACETS['test']),
            **{k: 'SYNTHETIC CHECKER INPUT, NOT PRODUCTION EXECUTION' for k in ('command', 'toolchain', 'engine', 'timestamp', 'seed')})
        reports[cohort] = bind_report(dict(version=1, source_revision=REVISION, inventory_sha256=sha(q/'inventory.json'), results=[row]),
                                     inventory, 'inventory.json', sha(q/'inventory.json'))
    require((q/'build-a/template.wat').read_bytes() == (q/'build-b/template.wat').read_bytes() and
            (q/'build-a/module.wasm').read_bytes() != (q/'build-b/module.wasm').read_bytes(), 'TEMPLATE_BINARY_DISTINCTION')
    (q/'stale-template.wat').write_bytes((q/'build-a/template.wat').read_bytes().replace(b'@VALUE@', b'0'))
    changed = copy.deepcopy(inventory)
    changed['tests'][0]['assertions'][0]['description'] += '; changed required contract'
    save(q/'changed-current-inventory.json', changed)
    return reports


def mutate(bases, case):
    report = copy.deepcopy(bases[case.get('cohort', 'a')]); row = report['results'][0]
    op = case['mutation']; facet = case.get('facet')
    inventory = 'inventory.json'
    if facet: artifact = next(a for a in row['artifacts'] if a['role'] == facet)
    if op == 'none': pass
    elif op == 'mixed': artifact['path'] = 'stale-template.wat' if facet == 'template' else 'build-b/'+FACETS[facet]
    elif op == 'missing-file': artifact['path'] = 'absent/'+FACETS[facet]
    elif op == 'omit-role': row['artifacts'].remove(artifact)
    elif op == 'duplicate-masks-abi':
        row['artifacts'] = [copy.deepcopy(next(a for a in row['artifacts'] if a['role'] == 'test')) if a['role'] == 'abi' else a for a in row['artifacts']]
    elif op == 'template-as-binary-hash':
        next(a for a in row['artifacts'] if a['role'] == 'installed-binary')['sha256'] = next(a for a in row['artifacts'] if a['role'] == 'template')['sha256']
    elif op == 'source-revision': row['source_revision'] = 'OTHER-SYNTHETIC-REVISION'
    elif op == 'changed-contract': inventory = 'changed-current-inventory.json'
    elif op == 'stale-snapshot': row['contract_binding']['inventory_sha256'] = '0'*64
    elif op == 'unreviewed': row['review_disposition'] = 'NOT_REVIEWED'
    else: raise ValueError('UNKNOWN_MUTATION '+op)
    return report, inventory


def invoke(inventory, report):
    argv = [sys.executable, str(TOOLS/'gate.py'), '--inventory', str(inventory), '--results', str(report)]
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15)
    return dict(command=argv, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)


def expected(observation, case):
    require(observation['exit_code'] == {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[case['expected']['status']]
            and observation['stderr'] == '' and json.loads(observation['stdout']) == case['expected'],
            'UNEXPECTED_GATE_RESULT '+case['name'])


def case_inventory(cases):
    require(cases == read(HERE/'cases.json') and cases['test_id'] == ID and len(cases['cases']) == 38 and
            len({c['name'] for c in cases['cases']}) == 38, 'CASE_BOUND')
    for mutation in ('mixed', 'missing-file', 'omit-role'):
        require([c['facet'] for c in cases['cases'] if c['mutation'] == mutation] == list(FACETS), 'FACET_COVERAGE')


def exercise(out, cases, bases, replay=False):
    commands, observations = [], []
    for case in cases['cases']:
        report, inventory = mutate(bases, case)
        path = out/'quarantine'/(case['name']+'.json')
        if replay: require(read(path) == report, 'RETAINED_CASE '+case['name'])
        else: save(path, report)
        # Paths/hashes, rather than the inner PASS label, decide these results.
        try: result = invoke(out/'quarantine'/inventory, path)
        except subprocess.TimeoutExpired as e:
            if not replay: save(out/'commands.json', commands+[dict(case=case['name'], error='TIMEOUT', command=e.cmd)])
            raise
        commands.append(dict(case=case['name'], **result))
        if not replay: save(out/'commands.json', commands)
        expected(result, case)
        observations.append(dict(case=case['name'], exit_code=result['exit_code'], result=json.loads(result['stdout']),
            declared_artifacts=report['results'][0]['artifacts']))
    return observations


def slot_gate(out):
    subset = read(out/'inventory.json'); subset['tests'] = [t for t in subset['tests'] if t['id'] == ID]
    save(out/'slot-inventory.json', subset)
    result = invoke(out/'slot-inventory.json', out/'results.json')
    save(out/'slot-gate.json', dict(exit_code=result['exit_code'], result=json.loads(result['stdout']), stderr=result['stderr']))
    expected(result, dict(name='real slot', expected=dict(status='BLOCKED', reasons=['unreviewed S0-LL22-a [control]'])))


def run(out):
    require(out != ROOT and ROOT not in out.parents, 'USE_FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv],
        timestamp=datetime.now(timezone.utc).isoformat(), source_sha256={str(p.relative_to(ROOT)): sha(p) for p in source_paths()})
    try:
        inventory_path = ROOT/'doc/WASM/stage0/inventory.json'; inventory = read(inventory_path)
        test = next(t for t in inventory['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT)/'run.py') and test['variants'] == ['control'], 'UNREGISTERED_RUNNER')
        (out/'source').mkdir()
        for p in source_paths(): (out/'source'/p.name).write_bytes(p.read_bytes())
        (out/'inventory.json').write_bytes(inventory_path.read_bytes())
        cases = read(HERE/'cases.json'); case_inventory(cases); save(out/'cases.json', cases)
        bases = fixture(out/'quarantine')
        observations = exercise(out, cases, bases); save(out/'observations.json', observations)
        require({s: sum(r['result']['status'] == s for r in observations) for s in ('PASS', 'FAIL', 'BLOCKED')}
                == dict(PASS=2, FAIL=35, BLOCKED=1), 'RESULT_COUNTS')
        save(out/'summary.json', dict(version=1, id=ID, variant='control', status='PASS', review_disposition='NOT_REVIEWED',
            scope=cases['scope'], facets=list(FACETS), positive_cases=2, rejected_cases=36,
            mixed_or_stale_bytes_rejected=10, absent_files_rejected=10, omitted_roles_rejected=10,
            same_template_distinct_binary_hashes=True, production_compiler_or_wasm_execution=False))
        environment = dict(python=sys.version, executable=sys.executable, executable_sha256=sha(Path(sys.executable).resolve()), platform=platform.platform())
        save(out/'environment.json', environment)
        artifacts = [dict(path=str(p.relative_to(out)), sha256=sha(p), role=(
            'implementation' if p.name in ('gate.py', 'evidence_binding.py') else
            'test' if p.name == 'run.py' else 'schema' if p.name in ('cases.json', 'inventory.json') else 'log'))
            for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'run.json']
        report = dict(version=1, source_revision=inventory['source_revision'], inventory_sha256=sha(out/'inventory.json'),
            scope='Production-gate artifact identity control; all inner records and payloads are synthetic.',
            results=[dict(id=ID, variant='control', source_revision=test['source_revision'], evidence_kind=test['evidence_kind'],
                status='PASS', assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']],
                artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED', command=record['command'],
                toolchain=environment, engine='Python production gate CLI', timestamp=record['timestamp'],
                configuration=cases['scope'], seed='deterministic named artifact-identity controls',
                test_revision=record['source_sha256'][str((HERE/'run.py').relative_to(ROOT))])])
        save(out/'results.json', bind_report(report, inventory, 'inventory.json', sha(out/'inventory.json')))
        slot_gate(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in source_paths()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inventory, ID))
        print('PASS: S0-LL22-a; 2 complete inputs, 36 rejected controls across 10 artifact facets. Slot awaits review/acceptance.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e); raise
    finally: save(out/'run.json', record)


def verify(packet):
    record = read(packet/'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, digest in record['source_sha256'].items(): require(sha(ROOT/name) == digest, 'SOURCE_PIN '+name)
    cases = read(packet/'cases.json'); case_inventory(cases)
    with tempfile.TemporaryDirectory(prefix='ccl-artifact-verification-') as tmp:
        q = Path(tmp)/'quarantine'; bases = fixture(q)
        expected_paths = {str(p.relative_to(q)) for p in q.rglob('*') if p.is_file()}
        got_paths = {str(p.relative_to(packet/'quarantine')) for p in (packet/'quarantine').rglob('*') if p.is_file()}
        require(got_paths == expected_paths | {c['name']+'.json' for c in cases['cases']}, 'RETAINED_FILE_BOUND')
        for name in expected_paths: require((q/name).read_bytes() == (packet/'quarantine'/name).read_bytes(), 'FIXTURE_BYTES '+name)
        observations = exercise(packet, cases, bases, replay=True)
    require(observations == read(packet/'observations.json'), 'OBSERVATIONS')
    result = invoke(packet/'slot-inventory.json', packet/'results.json')
    expected(result, dict(name='retained real slot', expected=dict(status='BLOCKED', reasons=['unreviewed S0-LL22-a [control]'])))
    print('PASS: 38 retained production-gate cases, exact fixture bytes and declarations, direct pins and real-slot envelope.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path)
    a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
