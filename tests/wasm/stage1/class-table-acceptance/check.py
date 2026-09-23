"""Bind the integrated files to audit 164's already-qualified proposal.

This is an identity check, not another execution run. The original verifier
replays from a7d33401; its source pins intentionally precede integration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
PACKET = '2026-09-23-stage1-class-table-r1'
PACKET_SHA = '790f0506420bad9a4d6fde9bea4164a73b84e00a8133d97ad617db6ea1c62004'
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'
COMPILER_SHA = '13e984cad8c00f88e4d66eeee556c36a73d2c44010189ef442043f3c5225efaf'
REVIEW = 'e919cb6f259ccb9c12ca52647875d788c398f4b7'
REVIEW_PATH = 'doc/WASM/stage0/claude-review.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def check(store):
    packet = store / PACKET
    assert sha(packet / 'packet.json') == PACKET_SHA
    listed = {row['path']: row['sha256'] for row in read(packet / 'packet.json')['files']}

    def bound(name):
        path = packet / name
        assert sha(path) == listed[name], name
        return read(path)

    summary = bound('summary.json')
    native = bound('native/run.json')
    manifest = bound('native/proposal/unit.json')
    pins = bound('source-pins.json')
    assert summary['compiler_sha256'] == COMPILER_SHA
    assert native['status'] == 'PASS'
    assert native['registered_tests']['passed'] == summary['native_tests'] == 21843
    assert sha(ROOT / BACKEND) == COMPILER_SHA
    assert '(defvar *b-cpl-conditions* nil)' in (ROOT / BACKEND).read_text()

    # Native qualification covers the complete proposal applied to pristine U1.
    # Unmodified source and the runtime retain the packet's execution inputs.
    qualified = {row['path']: row.get('after', row.get('sha256'))
                 for row in manifest['added'] + manifest['modified']}
    for name, digest in qualified.items():
        assert sha(ROOT / name) == digest, name
    checked = 0
    for name, digest in pins.items():
        if name.startswith(('compiler/', 'level-0/', 'level-1/', 'lib/',
                            'library/', 'xdump/', 'runtime/wasm32/')):
            assert sha(ROOT / name) == qualified.get(name, digest), name
            checked += 1

    acceptance = read(ROOT / 'doc/WASM/stage1/acceptance-class-table.json')
    review = subprocess.check_output(['git', 'show', REVIEW + ':' + REVIEW_PATH], cwd=ROOT)
    assert acceptance['review']['sha256'] == hashlib.sha256(review).hexdigest()
    assert acceptance['review']['commit'] == REVIEW
    return dict(status='PASS', mode='SOURCE_IDENTITY_AND_QUALIFICATION_REUSE',
                packet=PACKET, packet_sha256=PACKET_SHA,
                compiler_sha256=COMPILER_SHA, qualified_files=len(qualified),
                unchanged_or_qualified_source_files=checked,
                comparisons_reused=summary['comparisons'],
                native_tests_reused=summary['native_tests'],
                original_definition_headline=summary['original_definition_headline'],
                original_non_nil_headline=summary['original_non_nil_headline'],
                new_execution=False, slot_credit=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT.parent / 'ccl-evidence')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.evidence.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
