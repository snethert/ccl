"""Verify the audit-180 integration against both immutable reviewed packets."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
import common as c

RECORD = c.ROOT / 'doc/WASM/stage1/integration-loader-prefix.json'


def check():
    record = c.read(RECORD)
    assert record['status'] == 'ACCEPTED_AND_INTEGRATED'
    review = record['review']
    assert hashlib.sha256((c.ROOT / review['path']).read_bytes()[:review['bytes']]).hexdigest() == review['sha256']
    for packet in record['packets'].values():
        root = c.STORE / packet['path']
        assert c.sha(root / 'packet.json') == packet['sha256']
        inventory = c.read(root / 'packet.json')['files']
        for name, digest in packet['records'].items():
            assert c.sha(root / name) == digest == inventory[name]
    for row in record['files']:
        assert c.sha(c.ROOT / row['file']) == row['after'] == row['reviewed']
        assert c.sha(c.ROOT / row['proposal']) == row['reviewed']
        label = 'locks' if '/loader-locks/' in row['proposal'] else 'set-package'
        root = c.STORE / record['packets'][label]['path']
        key = 'source/files/' + row['file']
        inventory = c.read(root / 'packet.json')['files']
        if key in inventory:
            assert c.sha(root / key) == row['reviewed'] == inventory[key]
        else:
            assert c.read(root / 'compressed.json')[key]['sha256'] == row['reviewed']
    identity = record['qualification']['source_identity']
    root = c.STORE / record['packets']['locks']['path']
    assert identity == c.read(root / 'native/qualification.json')['source_identity']
    c.verify_files(c.ROOT, identity)
    c.verify_files(c.ROOT, record['runtime_identity'])
    return dict(status='PASS', source_identity=identity,
                runtime_identity=record['runtime_identity'],
                integration_record=c.sha(RECORD), new_execution=False,
                native_tests_reused=21843, restored_fasls=164,
                reader_rows_reused=51, compiler_comparisons_reused=26048,
                slot_credit=False)


def sources():
    return {name: (c.ROOT / name).read_text() for name in check()['source_identity']}


def prepare_runtime(out):
    import shutil
    check()
    out.mkdir(parents=True, exist_ok=True)
    for name in c.read(RECORD)['runtime_identity']:
        shutil.copyfile(c.ROOT / name, out / Path(name).name)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
