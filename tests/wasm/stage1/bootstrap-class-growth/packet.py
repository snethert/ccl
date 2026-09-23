"""Retain/replay native condition construction with final-source qualification."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STORE = ROOT.parent / 'ccl-evidence'
sys.path.insert(0, str(HERE))
from check import check
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def files(path):
    return sorted(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)


def sources():
    # Pin the static source set, not a recursively rediscovered set on replay.
    # This includes the inherited drivers without copying them into this unit.
    parent = read(STORE / '2026-09-23-stage1-class-table-r1/source-pins.json')
    paths = {ROOT / name for name in parent}
    paths.update(files(HERE))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}



def artifacts(out):
    selected = {row['name'] for row in read(out / 'compiled/modules.json')}
    selected.add('collector_probe_hook')
    result = {}
    for p in files(out):
        name = p.relative_to(out)
        if name.parts[0] == 'driver' or p.name in ('command.json', 'native-read-skips.sexp', 'verification.json'):
            continue
        if name.parts[0] == 'compiled' and len(name.parts) == 2 and p.suffix in ('.wasm', '.wat') and p.stem not in selected:
            continue
        if p.suffix not in ('.json', '.wasm', '.wat', '.lisp', '.mjs', '.c', '.h', '.legacy'):
            continue
        result[str(name)] = sha(p)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('retain', 'verify'))
    for name in ('packet', 'output', 'native'):
        parser.add_argument('--' + name, type=Path, required=name != 'native')
    parser.add_argument('--reuse-output', action='store_true', help='Validate an already completed run; do not claim a new replay.')
    args = parser.parse_args()
    packet, out = args.packet.resolve(), args.output.resolve()
    dependency_names = (
        '2026-09-23-stage1-condition-system-r1/packet.json',
        '2026-09-23-stage1-condition-system-r1/execution.tar.gz',
        '2026-09-23-stage1-condition-system-acceptance/packet.json',
        '2026-09-23-stage1-class-table-r1/packet.json',
        '2026-09-23-stage1-class-table-acceptance/packet.json',
        '2026-09-21-stage1-population-pushnew-r1/execution/eql.wasm',
        'macos-u1-inputs/source.tar', 'macos-u1-inputs/bootstrap.tar.gz', 'macos-u1-inputs/tests.tar',
        '2026-09-12-native-census-r7/baseline/build/dx86cl64',
        '2026-09-16-stage1-1a-r2/native/baseline.image')
    dependencies = {name: sha(STORE / name) for name in dependency_names}
    tools = {name: sha(Path(name)) for name in ('/usr/local/bin/node', '/usr/local/bin/wat2wasm', '/usr/local/opt/llvm/bin/clang')}
    if args.mode == 'retain':
        native = args.native.resolve()
        check(out, native)
        packet.mkdir()
        deterministic = artifacts(out)
        save(packet / 'deterministic.json', deterministic)
        save(packet / 'source-pins.json', sources())
        save(packet / 'dependencies.json', dependencies)
        save(packet / 'tools.json', tools)
        shutil.copyfile(out / 'summary.json', packet / 'summary.json')
        with tarfile.open(packet / 'execution.tar.gz', 'w:gz', dereference=True) as archive:
            for name in deterministic:
                archive.add(out / name, arcname=name, recursive=False)
            for name in ('execution.log', 'compiled/compile.log'):
                archive.add(out / name, arcname=name, recursive=False)
        # Keep the actual compiler and complete generated driver for review
        # probes. Native FASLs contain source locations, so this is a bound
        # build artifact, not part of the byte-identical replay comparison.
        review = [out / 'compiled/compiler.dx64fsl', out / 'compiled/command.json'] + files(out / 'driver')
        save(packet / 'review-artifacts.json', {
            'files': {str(p.relative_to(out)): sha(p) for p in review},
            'wabt_workers': 4,
            'execution_workers': 1,
            'scope': 'Retained compiler and generated drivers. No compile-cache or focused-probe command is claimed.'})
        with tarfile.open(packet / 'review-artifacts.tar.gz', 'w:gz', dereference=True) as archive:
            for p in review:
                archive.add(p, arcname=str(p.relative_to(out)), recursive=False)
        omitted = {}
        for p in files(native):
            name = p.relative_to(native)
            if p.name in ('baseline.image', 'registered.image', 'baseline-fasls.tar.gz') or name.parts[0] == 'baseline-tests':
                omitted[str(name)] = sha(p)
                continue
            target = packet / 'native' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
        save(packet / 'native/reused-or-regenerable.json', omitted)
        shutil.copytree(HERE, packet / 'source', ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet / 'development.tar.gz', 'w:gz') as archive:
            for name in ('ccl-class-growth-r1-execute.log', 'ccl-class-growth-r2/execution.log',
                         'ccl-class-growth-r2-focused.log', 'ccl-class-growth-r3/compiled/compile.log',
                         'ccl-class-growth-r4.log', 'ccl-class-undefined-observation.json',
                         'ccl-class-growth-r5/execution.log',
                         'ccl-class-growth-r5-focused.log', 'debug-class-growth-execution-2.log',
                         'ccl-class-growth-r6/execution.log', 'debug-class-growth6.log',
                         'ccl-class-growth-r6/driver/numeric-files.lisp',
                         'ccl-class-growth-r7/execution.log', 'ccl-class-growth-r7/driver/arch-probes.lisp',
                         'ccl-class-growth-r9/execution.log', 'class-growth-undefined-debug.log',
                         'class-growth-float-debug.log', 'ccl-class-growth-r9/driver/arch-probes.lisp',
                         'ccl-class-growth-r9/compiled/proposal/files/level-0/WASM32/w32-prims.lisp',
                         'ccl-class-growth-r2/driver/arch-probes.lisp',
                         'ccl-class-growth-r3/driver/arch-probes.lisp',
                         'ccl-class-growth-r5/driver/arch-probes.lisp',
                         'ccl-class-growth-r5/compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp'):
                archive.add(Path('/tmp') / name, arcname=name, recursive=False)

        save(packet / 'packet.json', dict(id='STAGE1-CLASS-GROWTH-R1',
            review_disposition='NOT_REVIEWED', slot_credit=False,
            files=[dict(path=str(p.relative_to(packet)), sha256=sha(p), bytes=p.stat().st_size) for p in files(packet)]))
    else:
        for name, digest in read(packet / 'source-pins.json').items():
            assert sha(ROOT / name) == digest, name
        assert dependencies == read(packet / 'dependencies.json')
        assert tools == read(packet / 'tools.json')
        entries = read(packet / 'packet.json')['files']
        assert {r['path'] for r in entries} == {str(p.relative_to(packet)) for p in files(packet) if p.name != 'packet.json'}
        for row in entries:
            assert sha(packet / row['path']) == row['sha256'], row['path']
        if not args.reuse_output:
            subprocess.run([sys.executable, HERE / 'run.py', out], check=True)
        summary = check(out, packet / 'native')
        actual, expected = artifacts(out), read(packet / 'deterministic.json')
        assert actual == expected, sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        save(out / 'verification.json', dict(status='PASS', deterministic_files=len(actual),
            source_pins=len(read(packet / 'source-pins.json')), summary=summary,
            native_reused_by_final_source_hash=True,
            execution_rebuilt=not args.reuse_output))


if __name__ == '__main__':
    main()
