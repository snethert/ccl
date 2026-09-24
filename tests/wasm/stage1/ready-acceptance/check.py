"""Bind the integrated READY compiler to the reviewed R9 execution.

No execution is performed. Replay the original READY packet at f48be155;
its derivation and source pins intentionally precede this integration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
PACKET = '2026-09-24-stage1-ready-join-r9'
PACKET_SHA = '8d7b8ff2399bb4f188a56198c25dcb3998410bfb8757e9c71e9576dfe0d7b463'
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())



def check_bit_layout(worker, reviewed_worker):
    # Bind the observation that killed the bit-order mutant, rather than
    # unrelated later stream/lock witnesses in the same worker file.
    start = "        if(name==='READY-BIT-VECTORS'){"
    end = '          const end=memory.buffer.byteLength,tail=end-8;'
    def observation(text):
        assert text.count(start) == text.count(end) == 1
        block = text.split(start, 1)[1].split(end, 1)[0]
        assert "'bit tail'" in block and "'zero bit padding'" in block
        return block
    assert observation(worker) == observation(reviewed_worker), 'raw bit layout observation changed'


def reviewed(store, revision=None):
    packet = store / PACKET
    assert sha(packet / 'packet.json') == PACKET_SHA
    files = read(packet / 'packet.json')['files']

    def bound(name):
        path = packet / name
        assert sha(path) == files[name], name
        return read(path)

    identity = bound('native-proposal-identity.json')
    assert identity == bound('native-reuse.json')['source_identity']
    assert sha(packet / ('proposal/' + BACKEND)) == identity[BACKEND]
    assert files['proposal/' + BACKEND] == identity[BACKEND]
    def source(name):
        if revision:
            return subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
        return (ROOT / name).read_bytes()
    for name, digest in identity.items():
        assert hashlib.sha256(source(name)).hexdigest() == digest, name
    assert source(BACKEND) == (packet / 'proposal' / BACKEND).read_bytes()
    pins = bound('pins.json')
    for name, digest in pins.items():
        if name.startswith('runtime/wasm32/'):
            assert hashlib.sha256(source(name)).hexdigest() == digest, name
    # Keep the independent representation observation, not just shared-helper
    # Lisp round trips. Audit 173's reversed-bit-order mutant needs this check.
    worker = (ROOT / 'tests/wasm/stage1/ready/worker.mjs').read_text()
    original_worker = (packet / 'source/worker.mjs').read_text()
    check_bit_layout(worker, original_worker)
    assert ':admitted)' in (ROOT / 'tests/wasm/stage1/ready/compiler.py').read_text()
    return packet, identity, bound


def check(store):
    revision = "7668f42d"
    packet, identity, bound = reviewed(store, revision)
    summary = bound('summary.json')
    native = bound('native-run.json')
    assert native['status'] == summary['status'] == 'PASS'
    assert native['registered_tests']['passed'] == 21843
    acceptance = read(ROOT / 'doc/WASM/stage1/acceptance-ready-compiler.json')
    review = acceptance['review']
    data = subprocess.check_output(['git', 'show', review['commit'] + ':' + review['path']], cwd=ROOT)
    assert hashlib.sha256(data).hexdigest() == review['sha256']
    assert acceptance['packet']['sha256'] == PACKET_SHA
    return dict(status='PASS', mode='HISTORICAL_SOURCE_AND_CURRENT_RAW_LAYOUT',
                source_revision=revision,
                packet=PACKET, packet_sha256=PACKET_SHA,
                compiler_sha256=identity[BACKEND], qualified_source_identity=identity,
                comparisons_reused=summary['full_corpus_comparisons'],
                cold_boots_reused=summary['cold_boots'],
                control_transition={'bit-vector-kind': 'refused -> admitted'},
                raw_bit_layout_check_preserved=True, new_execution=False,
                slot_credit=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT.parent / 'ccl-evidence')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'qualified_source_identity'}))
