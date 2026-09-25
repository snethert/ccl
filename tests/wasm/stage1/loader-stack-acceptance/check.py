"""Bind the audit-181 integration to its immutable qualification records."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
import common as c
RECORD = c.ROOT / 'doc/WASM/stage1/integration-loader-stack.json'


def read(root, name):
    path = root / name
    if path.is_file():
        return c.read(path)
    return json.loads(gzip.decompress(path.with_name(path.name + '.gz').read_bytes()))


def check():
    record = c.read(RECORD)
    assert record['status'] == 'ACCEPTED_AND_INTEGRATED'
    review = record['review']
    assert hashlib.sha256((c.ROOT / review['path']).read_bytes()[:review['bytes']]).hexdigest() == review['sha256']
    inventories = {}
    for label, packet in record['packets'].items():
        root = c.STORE / packet['path']
        assert c.sha(root / 'packet.json') == packet['sha256']
        inventories[label] = c.read(root / 'packet.json')['files']
        for name, digest in packet['records'].items():
            assert c.sha(root / name) == digest == inventories[label][name]
    for row in record['files']:
        assert c.sha(c.ROOT / row['file']) == row['after'] == row['reviewed']
        assert c.sha(c.ROOT / row['proposal']) == row['reviewed']
        label = ('definitions' if '/loader-def/' in row['proposal'] else
                 'pointer' if '/loader-new-ptr/' in row['proposal'] else 'aref')
        root = c.STORE / record['packets'][label]['path']
        name = 'source/files/' + row['file']
        if row['file'] == 'runtime/wasm32/collector.c':
            assert c.read(root / 'collector/summary.json')['source'] == row['reviewed']
        elif name in inventories[label]:
            assert c.sha(root / name) == row['reviewed'] == inventories[label][name]
        else:
            assert c.read(root / 'compressed.json')[name]['sha256'] == row['reviewed']
    root = c.STORE / record['packets']['definitions']['path']
    sources = record['qualification']['source_identity']
    assert sources == c.read(root / 'native/qualification.json')['source_identity']
    assert c.read(root / 'native/results/run.json')['status'] == 'PASS'
    reader_rows = 0
    for label in ('pointer', 'definitions'):
        readers = c.read(c.STORE / record['packets'][label]['path'] / 'readers/summary.json')
        assert readers['status'] == 'PASS' and readers['profiles'] == 17
        # Foreign-form normalization has separate before/after hashes. Bind
        # the full source containing those unchanged forms as well.
        assert all(sources[n] == row['after'] for n, row in readers['full_sources'].items())
        reader_rows += readers['comparisons']
    assert reader_rows == record['qualification']['reader_rows'] == 68
    regression = c.read(root / 'corpus/regression.json')
    execution = read(root, 'execution/summary.json')
    assert regression['status'] == 'PASS' and regression['fresh_comparisons'] == 26048
    assert regression['runtime'] == execution['runtime']
    assert read(root, 'corpus/base/execution-environment.json')['files']['collector.wasm'] == execution['runtime']['binary']
    collector = c.read(c.STORE / record['packets']['aref']['path'] / 'collector/summary.json')
    assert collector['status'] == 'PASS' and collector['source'] == execution['runtime']['source']
    c.verify_files(c.ROOT, sources)
    c.verify_files(c.ROOT, record['runtime_identity'])
    assert c.sha(c.ROOT / 'runtime/wasm32/collector.c') == execution['runtime']['source']
    return dict(status='PASS', source_identity=sources, runtime_identity=record['runtime_identity'],
                integration_record=c.sha(RECORD), new_execution=False,
                native_tests_reused=21843, restored_fasls=164, reader_rows_reused=68,
                compiler_comparisons_reused=26048, collector_checks_reused=46, slot_credit=False)


def sources():
    return {name: (c.ROOT / name).read_text() for name in check()['source_identity']}


def prepare_runtime(out):
    check()
    out.mkdir(parents=True, exist_ok=True)
    for name in c.read(RECORD)['runtime_identity']:
        shutil.copyfile(c.ROOT / name, out / Path(name).name)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
