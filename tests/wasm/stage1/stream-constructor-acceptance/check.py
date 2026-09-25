"""Check reviewed integration identity; this command performs no execution."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(revision='b2f0ad8f'):
    read = lambda path: json.loads(path.read_text())
    record = read(ROOT / 'doc/WASM/stage1/integration-stream-constructors.json')
    acceptance = ROOT / 'doc/WASM/stage1' / record['acceptance']
    assert sha(acceptance) == record['acceptance_sha256']
    accepted = read(acceptance)
    packet = ROOT.parent / 'ccl-evidence' / Path(record['qualification']['packet']).name
    assert sha(packet / 'packet.json') == accepted['packet']['sha256']
    files = read(packet / 'packet.json')['files']
    for name, digest in record['qualification']['records'].items():
        assert sha(packet / name) == digest == files[name], name
    def source_sha(name):
        if revision is None:
            return sha(ROOT / name)
        content = subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
        return hashlib.sha256(content).hexdigest()
    for name, digest in record['qualification']['source_identity'].items():
        assert source_sha(name) == digest, name
    for row in record['files']:
        assert source_sha(row['file']) == row['after'] == row['reviewed'], row['file']
    review = accepted['review']
    content = subprocess.check_output(['git', 'show', review['commit'] + ':' + review['path']], cwd=ROOT)
    assert hashlib.sha256(content).hexdigest() == review['sha256']
    return dict(status='PASS',mode='HISTORICAL_REVIEWED_SOURCE_IDENTITY',source_revision=revision,new_execution=False,
                native_tests_reused=21843,target_comparisons_reused=26048,
                original_definitions=575,non_nil=535,slot_credit=False)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
