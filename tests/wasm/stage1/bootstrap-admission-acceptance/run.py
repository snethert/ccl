"""Integrate audit 153's exact sources, moving arch macros without changing forms."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIXTURE = HERE.parent / 'bootstrap-admission'
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'
ARCH = 'compiler/WASM32/wasm32-arch.lisp'
PACKET_NAME = '2026-09-21-stage1-bootstrap-admission-r1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def final_files(packet):
    proposal = packet / 'execution/compiled/proposal'
    manifest = json.loads((proposal / 'unit.json').read_text())
    result = {}
    for row in manifest['added'] + manifest['modified']:
        path = proposal / 'files' / row['path']
        assert sha(path) == row.get('sha256', row.get('after')), row['path']
        result[row['path']] = path.read_bytes()
    macros = (packet / 'source/target-macros.lisp').read_bytes()
    assert result[BACKEND].endswith(b'\n' + macros)
    result[BACKEND] = result[BACKEND][:-len(macros)-1]
    # ARCH loads first. Establish the same package in which the reviewed macro
    # forms were read; BACKEND's identical DEFPACKAGE remains idempotent.
    result[ARCH] += (b'\n(cl:defpackage "WASM32-COMPILER" (:use "CL"))\n'
                     b'(cl:in-package "WASM32-COMPILER")\n' + macros)
    return manifest, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('install', 'native', 'target'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--evidence', type=Path, default=ROOT.parent / 'ccl-evidence')
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    packet = evidence / PACKET_NAME
    index = json.loads((ROOT / 'doc/WASM/evidence/index.json').read_text())
    row = next(r for r in index['auxiliary_records'] if r['id'] == 'STAGE1-BOOTSTRAP-ADMISSION-R1')
    assert sha(packet / 'packet.json') == row['sha256']
    manifest, final = final_files(packet)
    out = args.output.resolve()
    if args.mode == 'install':
        out.mkdir()
        changes = []
        for name, data in final.items():
            path = ROOT / name
            before = sha(path)
            if path.read_bytes() != data:
                path.write_bytes(data)
                changes.append(dict(file=name, before=before, after=sha(path),
                                    reviewed=sha(packet / 'execution/compiled/proposal/files' / name)))
        save(out / 'changes.json', changes)
        return
    # Execute the installed bytes, not another derivation from the old backend.
    for name, data in final.items():
        assert (ROOT / name).read_bytes() == data, name

    def proposal(src, dest):
        shutil.copytree(packet / 'execution/compiled/proposal', dest)
        result = json.loads((dest / 'unit.json').read_text())
        for row in result['added'] + result['modified']:
            path = dest / 'files' / row['path']
            path.write_bytes((ROOT / row['path']).read_bytes())
            row['sha256' if 'sha256' in row else 'after'] = sha(path)
        save(dest / 'unit.json', result)
        return result

    sys.path.insert(0, str(FIXTURE))
    import backend
    backend.generate = lambda: (ROOT / BACKEND).read_text()
    backend.arch_source = lambda: (ROOT / ARCH).read_text()
    backend.proposal = proposal
    backend.source_files = lambda src: {name: (ROOT / name).read_text() for name in final if name.startswith(('level-0/', 'level-1/'))}
    if args.mode == 'native':
        assert args.work is not None
        spec = importlib.util.spec_from_file_location('admission_native', FIXTURE / 'native.py')
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        status = native.driver.run(evidence / 'macos-u1-inputs',
                                  evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
                                  args.work.resolve(), out,
                                  evidence / '2026-09-16-stage1-1a-r2/native')
        assert status == 0, status
    else:
        import run
        run.compile_corpus(out)
        run.stable_reader_diagnostics(out)
        for name in ('execute.py', 'checks.py', 'host-checks.py'):
            subprocess.run([sys.executable, FIXTURE / name, out], check=True)
        run.summarize(out)
        old = packet / 'execution'
        matched = []
        for path in sorted((out / 'compiled').iterdir()):
            if path.suffix in ('.wat', '.wasm', '.legacy'):
                rel = path.relative_to(out)
                assert path.read_bytes() == (old / rel).read_bytes(), rel
                matched.append(str(rel))
        for name in ('compiled/native.json', 'compiled/closed.json', 'compiled/worklist-throughput.json',
                     'compiled/measure-controls.sexp', 'compiled/executed-operators.json',
                     'summary.json', 'execution.json', 'carry.json', 'host-protocol.json',
                     'member-witnesses.json', 'progress.json', 'istruct-checks.json'):
            if not (old / name).exists():
                raise AssertionError('unknown retained comparison: ' + name)
            assert (out / name).read_bytes() == (old / name).read_bytes(), name
            matched.append(name)
        save(out / 'integration.json', dict(status='PASS', identical_files=matched,
             final_files={name: sha(ROOT / name) for name in final},
             original_definitions_executed=382, non_nil_witness=355,
             scope='Macro relocation only; reviewed reader proof reused by exact CCL source identity. Runtime unchanged. No new execution credit.'))


if __name__ == '__main__':
    main()
