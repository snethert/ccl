"""Check integrated identity; reuse audit 168's completed execution."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]


def check():
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    acceptance = json.loads((ROOT / 'doc/WASM/stage1/acceptance-class-image.json').read_text())
    packet = Path(acceptance['packet']['locator'])
    assert sha(packet.read_bytes()) == acceptance['packet']['sha256']
    files = json.loads(packet.read_text())['files']

    def bound(name):
        data = (packet.parent / name).read_bytes()
        assert sha(data) == files[name], name
        return data

    source = bound('source/heap-image.mjs')
    prepared = source.replace(b"'../../../../runtime/wasm32/sha256.mjs'", b"'./sha256.mjs'")
    code = json.loads(bound('class-image-code.json'))
    runtime = ROOT / 'runtime/wasm32/heap-image.mjs'
    assert runtime.read_bytes() == prepared
    assert sha(prepared) == code['runtime/heap-image.mjs']
    assert sha((ROOT / 'runtime/wasm32/sha256.mjs').read_bytes()) == code['runtime/sha256.mjs']
    review = acceptance['review']
    assert sha(subprocess.check_output(['git', 'show', review['commit'] + ':' + review['path']], cwd=ROOT)) == review['sha256']
    return dict(status='PASS', mode='IDENTITY_AND_REVIEW_REUSE',
                runtime_sha256=sha(prepared), review=review['commit'],
                reused_summary=json.loads(bound('summary.json')),
                new_execution=False, slot_credit=False)


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
