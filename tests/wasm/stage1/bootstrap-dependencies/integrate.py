"""Check audit 148's mechanical fold against its pinned execution packet."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from fold import fold

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('native', 'target'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--evidence', type=Path, default=ROOT.parent / 'ccl-evidence')
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    packet = evidence / '2026-09-21-stage1-bootstrap-dependencies-r1'
    assert sha(packet / 'packet.json') == 'd7060e27fa5ed00e1b8898f28f7a9a6b3f59798c8c7f1f5bc379a6ac6316c50d'
    proposal_dir = packet / 'execution/compiled/proposal'
    assert sha(proposal_dir / 'unit.json') == '1bb82d8f0d28e3714c7bb305970812d639d6d6e9cd014af071431c6a8d1ecffb'
    manifest = json.loads((proposal_dir / 'unit.json').read_text())
    for row in manifest['added'] + manifest['modified']:
        assert sha(proposal_dir / 'files' / row['path']) == row.get('sha256', row.get('after'))
    final = fold((proposal_dir / 'files' / BACKEND).read_text())

    def proposal(src, out):
        shutil.copytree(proposal_dir, out)
        (out / 'files' / BACKEND).write_text(final)
        result = json.loads((out / 'unit.json').read_text())
        next(r for r in result['added'] if r['path'] == BACKEND)['sha256'] = sha(out / 'files' / BACKEND)
        (out / 'unit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        return result

    import backend
    backend.generate = lambda: final
    backend.proposal = proposal
    backend.source_files = lambda src: {
        row['path']: (proposal_dir / 'files' / row['path']).read_text()
        for row in manifest['added'] + manifest['modified']
        if row['path'].startswith('level-0/')}

    out = args.output.resolve()
    if args.mode == 'native':
        assert args.work is not None
        # The driver rebuilds all native FASLs with the final backend and
        # allows test reuse only on exact FASL and snapshot equality.
        sys.argv += ['--reuse-native', str(packet / 'native')]
        spec = importlib.util.spec_from_file_location('integration_native', HERE / 'native.py')
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        status = native.driver.run(
            evidence / 'macos-u1-inputs',
            evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
            args.work.resolve(), out, evidence / '2026-09-16-stage1-1a-r2/native')
        assert status == 0, status
    else:
        import run
        run.run(out)
        old = packet / 'execution'
        matched = []
        for path in sorted((out / 'compiled').glob('*')):
            if path.suffix in ('.wat', '.wasm', '.legacy'):
                rel = path.relative_to(out)
                assert path.read_bytes() == (old / rel).read_bytes(), str(rel)
                matched.append(str(rel))
        for name in ('compiled/native.json', 'compiled/closed.json', 'summary.json', 'execution.json', 'faults.json'):
            assert (out / name).read_bytes() == (old / name).read_bytes(), name
            matched.append(name)
        result = dict(status='PASS', reviewed_backend_sha256=sha(proposal_dir / 'files' / BACKEND),
                      integrated_backend_sha256=sha(out / 'compiled/proposal/files' / BACKEND),
                      identical_files=matched,
                      original_definitions_executed=252, definitions_with_non_nil_witness=193,
                      note='Witness split is audit 148\'s result; this fold adds no execution credit.')
        (out / 'integration.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
