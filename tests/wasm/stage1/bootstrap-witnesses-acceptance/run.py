"""Check audit 149's mechanical fold against its pinned execution packet."""
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
FIXTURE = HERE.parent / 'bootstrap-witnesses'
sys.path.insert(0,str(FIXTURE))
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
    packet = evidence / '2026-09-21-stage1-bootstrap-witnesses-r1'
    assert sha(packet / 'packet.json') == '45e7858663bf3219cc84ecc167f81dd3dc62c7660186c79a63db5516bb7a2673'
    proposal_dir = packet / 'execution/compiled/proposal'
    assert sha(proposal_dir / 'unit.json') == '6f18975b844d4d6978457fba9bc9611f41a96d77ef47b24f32e9d0d9ba0258b6'
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
    backend.runtime_files = lambda: {name: (packet / "execution/runtime" / name).read_text() for name in ("collector.c", "collector-owner.mjs")}
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
        spec = importlib.util.spec_from_file_location('integration_native', FIXTURE / 'native.py')
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        status = native.driver.run(
            evidence / 'macos-u1-inputs',
            evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
            args.work.resolve(), out, evidence / '2026-09-16-stage1-1a-r2/native')
        assert status == 0, status
    else:
        import run
        import subprocess
        run.compile_corpus(out)
        run.stable_reader_diagnostics(out)
        # The execution driver is a separate interpreter: pass the immutable
        # runtime source selection there as well, rather than relying on this
        # process's backend override.
        subprocess.run([sys.executable, HERE / 'execute.py', out, packet], check=True)
        subprocess.run([sys.executable, FIXTURE / 'faults.py', out], check=True)
        run.summarize(out)
        old = packet / 'execution'
        matched = []
        for path in sorted((out / 'compiled').glob('*')):
            if path.suffix in ('.wat', '.wasm', '.legacy'):
                rel = path.relative_to(out)
                assert path.read_bytes() == (old / rel).read_bytes(), str(rel)
                matched.append(str(rel))
        for name in ('compiled/native.json', 'compiled/closed.json', 'summary.json', 'execution.json', 'faults.json', 'compiled/executed-operators.json', 'member-witnesses.json', 'progress.json', 'istruct-checks.json'):
            assert (out / name).read_bytes() == (old / name).read_bytes(), name
            matched.append(name)
        result = dict(status='PASS', reviewed_backend_sha256=sha(proposal_dir / 'files' / BACKEND),
                      integrated_backend_sha256=sha(out / 'compiled/proposal/files' / BACKEND),
                      identical_files=matched,
                      original_definitions_executed=301, definitions_with_non_nil_witness=290,
                      note='Witness split is audit 149\'s result; this fold adds no execution credit.')
        # The prior owner suite has forty checks without its optional generated
        # boundary case. Run its exact source against the proposed runtime.
        import subprocess
        owner_dir=out/'owner-check';owner_dir.mkdir()
        for path in (out/'runtime').glob('*.mjs'):shutil.copy(path,owner_dir/path.name)
        shutil.copy(owner_dir/'collector-owner.mjs',owner_dir/'owner.mjs')
        check=ROOT/'tests/wasm/stage1/collector-owner/check.mjs'
        shutil.copy(check,owner_dir/'check.mjs')
        with (owner_dir/'run.log').open('w') as log:
            subprocess.run(['/usr/local/bin/node',owner_dir/'check.mjs',out/'collector.wasm',owner_dir/'results.json'],stdout=log,stderr=log,check=True)
        owner=json.loads((owner_dir/'results.json').read_text());assert owner['checks']==40 and owner['status']=='PASS'
        result['owner_checks']=40
        result['owner_check_source_sha256']=sha(check)
        result['collector_sha256']=sha(out/'collector.wasm')
        assert (out/'collector.wasm').read_bytes()==(packet/'execution/collector.wasm').read_bytes()
        (out / 'integration.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
