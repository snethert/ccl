#!/usr/bin/env python3
"""Contract-binding and migration controls; synthetic checker evidence only."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
from zipfile import ZIP_DEFLATED, ZipFile
sys.dont_write_bytecode = True
from evidence_binding import bind_report, binding_errors, contract_hash, digest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


gate, producer = load('gate', 'gate.py'), load('producer', 'bind-evidence.py')
archive_checker = load('archive_checker', 'check-evidence.py')
count = 0


def expect(actual, wanted, label):
    global count
    assert actual == wanted, (label, actual, wanted)
    count += 1


with tempfile.TemporaryDirectory(prefix='ccl-binding-controls-') as tmp:
    root = Path(tmp); source = root / 'source'; source.mkdir()
    (source / 'fixture').write_bytes(b'synthetic proof payload')
    roles = ['implementation', 'test', 'schema', 'log']
    def contract(ident, dependencies):
        return {'id': ident, 'source_revision': 'a' * 40, 'evidence_kind': 'CONTROL EXECUTION', 'variants': ['full'],
                'prerequisites': dependencies, 'runner': 'synthetic', 'assertions': [{'id': ident + ':value', 'description': 'check the full value'}],
                'status': 'IMPLEMENTED_NOT_ACCEPTED', 'review_disposition': 'NOT_REVIEWED'}
    inventory = {'version': 1, 'source_revision': 'a' * 40, 'required_record_roles': roles, 'acceptance_note': 'presentation',
                 'tests': [contract('A', ['P']), contract('P', [])]}
    raw_inventory = (json.dumps(inventory) + '\n').encode(); (source / 'inventory.json').write_bytes(raw_inventory)
    artifacts = [{'path': 'fixture', 'role': role, 'sha256': digest(b'synthetic proof payload')} for role in roles]
    records = []
    for test in inventory['tests']:
        record = {'id': test['id'], 'variant': 'full', 'status': 'PASS', 'source_revision': 'a' * 40, 'evidence_kind': 'CONTROL EXECUTION',
                  'substitutions': [], 'skips': [], 'review_disposition': 'ACCEPTED', 'review_record': 'synthetic only',
                  'assertions': [{'id': test['id'] + ':value', 'status': 'PASS'}], 'artifacts': copy.deepcopy(artifacts)}
        record.update({f: 'synthetic' for f in ['command', 'configuration', 'engine', 'toolchain', 'test_revision', 'seed', 'timestamp']})
        records.append(record)
    legacy = {'version': 1, 'source_revision': 'a' * 40, 'inventory_sha256': digest(raw_inventory), 'results': records}
    bound = bind_report(legacy, inventory, 'inventory.json', digest(raw_inventory))
    check = lambda inv, report: gate.assess(inv, report, digest(json.dumps(inv).encode()), source)
    expect(check(inventory, bound)[0], 'PASS', 'valid scoped binding')
    reordered = dict(reversed(list(inventory.items()))); reordered['tests'] = list(reversed(inventory['tests']))
    expect(contract_hash(inventory, 'A'), contract_hash(reordered, 'A'), 'object/test ordering is not semantic')
    unrelated = copy.deepcopy(inventory); unrelated['tests'].append(contract('NEW', []))
    status, reasons = check(unrelated, bound)
    expect((status, reasons), ('BLOCKED', ['missing NEW [full]']), 'unrelated addition preserves old evidence but blocks missing new result')
    for field in ['status', 'review_disposition']:
        changed = copy.deepcopy(inventory); changed['tests'][0][field] = 'new bookkeeping'
        expect(check(changed, bound)[0], 'PASS', 'bookkeeping field ' + field)
    changed = copy.deepcopy(inventory); changed['acceptance_note'] = 'new prose'
    expect(check(changed, bound)[0], 'PASS', 'inventory note does not invalidate')
    mutations = [
        lambda x: x['tests'][0]['assertions'][0].update(description='different meaning, same assertion ID'),
        lambda x: x['tests'][0].update(runner='different runner'),
        lambda x: x['tests'][0].update(variants=['full', 'extra']),
        lambda x: x['tests'][0].update(evidence_kind='OTHER EXECUTION'),
        lambda x: x['tests'][0].update(source_revision='b' * 40),
        lambda x: x['tests'][0].update(prerequisites=[]),
        lambda x: x['tests'][1]['assertions'][0].update(description='changed prerequisite'),
        lambda x: x.update(version=2),
        lambda x: x.update(version=True),
        lambda x: x.update(required_record_roles=roles + ['new required role']),
        lambda x: x['tests'][0].update(policy_sha256='b' * 64),
        lambda x: x.update(new_global_requirement='must be hashed'),
        lambda x: x['tests'][1].update(prerequisites=['A'])]
    for n, mutate in enumerate(mutations):
        changed = copy.deepcopy(inventory); mutate(changed)
        expect(check(changed, bound)[0], 'FAIL', 'semantic/dependency mutation ' + str(n))
    for field, value in [('contract_sha256', '0' * 64), ('inventory_sha256', '0' * 64), ('inventory_path', '../escape'),
                         ('inventory_path', 'missing.json'), ('inventory_version', True), ('version', 2)]:
        changed = copy.deepcopy(bound); changed['results'][0]['contract_binding'][field] = value
        expect(check(inventory, changed)[0], 'FAIL', 'invalid binding ' + field)
    changed = copy.deepcopy(bound); changed['results'][0].pop('contract_binding')
    expect(check(inventory, changed)[0], 'FAIL', 'missing binding')
    changed = copy.deepcopy(bound); changed['version'] = True
    expect(check(inventory, changed)[0], 'FAIL', 'boolean envelope version')
    (source / 'inventory.json').write_text(json.dumps(unrelated))
    expect(check(inventory, bound)[0], 'FAIL', 'rewritten original snapshot')
    (source / 'inventory.json').write_bytes(raw_inventory)
    expect(gate.assess(unrelated, legacy, 'f' * 64, source)[0], 'FAIL', 'legacy report cannot silently bypass its whole-file binding')
    source_report = source / 'legacy.json'; source_report.write_text(json.dumps(legacy))
    original_report = source_report.read_bytes()
    output = root / 'upgrade/results.json'
    producer.bind(source_report, source / 'inventory.json', output)
    migrated = json.loads(output.read_text())
    expect(gate.assess(inventory, migrated, 'f' * 64, output.parent)[0], 'PASS', 'explicit verified migration')
    expect(source_report.read_bytes(), original_report, 'migration preserves original report')
    expect([r['timestamp'] for r in migrated['results']], [r['timestamp'] for r in legacy['results']], 'migration preserves execution timestamps')
    def rejection(fn, label):
        try: fn()
        except (ValueError, OSError): expect(True, True, label)
        else: raise AssertionError(label)
    # Exercise the real CURRENT ZIP checker, including a mixed-version migration.
    package = root / 'package'; (package / 'stage0').mkdir(parents=True); (package / 'evidence').mkdir()
    archive_checker.ROOT = package
    (package / 'stage0/inventory.json').write_text(json.dumps(unrelated))
    pack = package / 'evidence/current.zip'
    def write_pack(report, corrupt_snapshot=False):
        with ZipFile(pack, 'w', compression=ZIP_DEFLATED) as archive:
            for path in sorted(output.parent.rglob('*')):
                if path.is_file() and path != output:
                    payload = path.read_bytes()
                    if corrupt_snapshot and path.name == 'inventory.json': payload += b' '
                    archive.writestr(path.relative_to(output.parent).as_posix(), payload)
            archive.writestr('results.json', json.dumps(report))
        index = {'current_runs': [{'id': 'synthetic ZIP', 'currency': 'CURRENT', 'path': 'evidence/current.zip',
                  'sha256': digest(pack.read_bytes()), 'inventory_sha256': report['inventory_sha256'], 'results_member': 'results.json'}]}
        (package / 'evidence/index.json').write_text(json.dumps(index))
    write_pack(migrated)
    expect(archive_checker.check(), 1, 'CURRENT ZIP survives unrelated inventory addition')
    write_pack(migrated, corrupt_snapshot=True)
    rejection(lambda: archive_checker.check(), 'CURRENT ZIP rejects rewritten snapshot even with refreshed archive hash')
    write_pack(migrated)
    index_path = package / 'evidence/index.json'; index = json.loads(index_path.read_text())
    index['current_runs'][0]['inventory_sha256'] = '0' * 64; index_path.write_text(json.dumps(index))
    rejection(lambda: archive_checker.check(), 'CURRENT index must preserve original inventory provenance')
    write_pack(legacy)
    rejection(lambda: archive_checker.check(), 'CURRENT legacy ZIP remains whole-file bound')
    for version in [True, 3]:
        invalid = copy.deepcopy(migrated); invalid['version'] = version; write_pack(invalid)
        rejection(lambda: archive_checker.check(), 'CURRENT ZIP rejects unsupported envelope version ' + str(version))
    rejection(lambda: producer.bind(source_report, source / 'inventory.json', output), 'migration cannot overwrite evidence')
    changed = copy.deepcopy(inventory); changed['tests'][0]['assertions'][0]['description'] = 'new semantics'
    current = root / 'current.json'; current.write_text(json.dumps(changed))
    rejection(lambda: producer.bind(source_report, source / 'inventory.json', root / 'bad/results.json', current), 'migration cannot bless changed semantics')
    (source / 'fixture').write_bytes(b'corrupted payload')
    rejection(lambda: producer.bind(source_report, source / 'inventory.json', root / 'corrupt/results.json'), 'migration verifies every retained artifact')
    (source / 'fixture').write_bytes(b'synthetic proof payload')
    failed = copy.deepcopy(legacy); failed['results'][0]['status'] = 'FAIL'; source_report.write_text(json.dumps(failed))
    producer.bind(source_report, source / 'inventory.json', root / 'failed/results.json')
    expect(json.loads((root / 'failed/results.json').read_text())['results'][0]['status'], 'FAIL', 'format upgrade preserves original failure')
print(f'PASS: {count} contract-binding and migration controls; no runtime acceptance claim.')
