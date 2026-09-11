#!/usr/bin/env python3
"""Synthetic controls for the authorized acceptance producer; no runtime claim."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from evidence_binding import bind_report, digest
from gate import assess

spec = importlib.util.spec_from_file_location('producer', Path(__file__).with_name('accept-evidence.py'))
producer = importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)
count = 0
with tempfile.TemporaryDirectory(prefix='ccl-acceptance-control-') as directory:
    root = Path(directory); source = root / 'source'; source.mkdir()
    (source / 'artifact').write_bytes(b'proof'); review = root / 'review.md'; review.write_text('synthetic review')
    inventory = {'version': 1, 'source_revision': 'a' * 40, 'required_record_roles': ['implementation', 'test', 'schema', 'log'],
                 'tests': [{'id': i, 'source_revision': 'a' * 40, 'runner': 'synthetic', 'variants': ['full'],
                            'evidence_kind': 'CONTROL EXECUTION', 'prerequisites': [], 'assertions': [{'id': i + ':contract'}]} for i in ['A', 'B']]}
    ip = source / 'inventory.json'; ip.write_text(json.dumps(inventory))
    records = []
    for i in ['A', 'B']:
        r = {k: 'synthetic' for k in ['command', 'toolchain', 'engine', 'timestamp', 'configuration', 'seed', 'test_revision']}
        r.update(id=i, variant='full', status='PASS', source_revision='a' * 40, evidence_kind='CONTROL EXECUTION',
                 skips=[], substitutions=[], review_disposition='NOT_REVIEWED', assertions=[{'id': i + ':contract', 'status': 'PASS'}],
                 artifacts=[{'path': 'artifact', 'sha256': digest(b'proof'), 'role': role} for role in inventory['required_record_roles']])
        records.append(r)
    report = bind_report({'version': 1, 'source_revision': 'a' * 40, 'inventory_sha256': digest(ip.read_bytes()), 'results': records},
                         inventory, 'inventory.json', digest(ip.read_bytes()))
    sp = source / 'results.json'; sp.write_text(json.dumps(report)); original = sp.read_bytes()
    decision = {'version': 1, 'operation': 'PROJECT_ACCEPTANCE_NO_EXECUTION', 'authorization': 'synthetic', 'timestamp': 'synthetic',
                'review_commit': 'b' * 40, 'scope': 'A only', 'exclusions': ['B'], 'source_report_sha256': digest(original),
                'review_sha256': digest(review.read_bytes()), 'records': [{'id': 'A', 'variant': 'full', 'test_revision': 'synthetic',
                    'contract_sha256': report['results'][0]['contract_binding']['contract_sha256'], 'scope': 'synthetic A'}]}
    dp = root / 'decision.json'
    def run(d, out):
        dp.write_text(json.dumps(d)); return producer.accept(sp, ip, dp, review, out)
    out = root / 'accepted/results.json'; run(decision, out)
    accepted = json.loads(out.read_text())
    assert assess(inventory, accepted, digest(ip.read_bytes()), out.parent) == ('BLOCKED', ['unreviewed B [full]']); count += 1
    assert sp.read_bytes() == original and accepted['results'][0]['timestamp'] == report['results'][0]['timestamp']; count += 1
    def reject(d, destination, label):
        global count
        try: run(d, destination)
        except ValueError: count += 1
        else: raise AssertionError(label)
    reject(decision, out, 'overwrite accepted record')
    for field in ['authorization', 'scope', 'review_commit']:
        d = copy.deepcopy(decision); del d[field]; reject(d, root / (field + '/results.json'), field)
    for field in ['source_report_sha256', 'review_sha256']:
        d = copy.deepcopy(decision); d[field] = '0' * 64; reject(d, root / (field + '/results.json'), field)
    for field in ['variant', 'test_revision', 'contract_sha256']:
        d = copy.deepcopy(decision); d['records'][0][field] = 'wrong'; reject(d, root / (field + '/results.json'), field)
    d = copy.deepcopy(decision); d['records'] *= 2; reject(d, root / 'duplicate/results.json', 'duplicate target')
    (source / 'artifact').write_bytes(b'corrupt'); reject(decision, root / 'corrupt/results.json', 'corrupt artifact')
    (source / 'artifact').write_bytes(b'proof')
    bad = copy.deepcopy(report); bad['results'][0]['assertions'][0]['status'] = 'FAIL'; sp.write_text(json.dumps(bad))
    d = copy.deepcopy(decision); d['source_report_sha256'] = digest(sp.read_bytes()); reject(d, root / 'failure/results.json', 'failed assertion')
print(f'PASS: {count} scoped acceptance controls; no runtime acceptance claim.')
