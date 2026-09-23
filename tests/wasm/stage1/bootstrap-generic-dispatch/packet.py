"""Retain and replay one complete bootstrap-standard dispatch proposal."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVIDENCE = ROOT.parent / 'ccl-evidence'
PARENT = EVIDENCE / '2026-09-22-stage1-method-dispatch-r1'
spec = importlib.util.spec_from_file_location('delta', HERE.parent / 'bootstrap-numeric-dispatch/packet.py')
delta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delta)
sha, read, save, files = delta.sha, delta.read, delta.save, delta.files


def pins():
    previous = read(PARENT / 'source-pins.json')
    for name, digest in previous.items():
        assert sha(ROOT / name) == digest, name
    return {**previous, **{str(p.relative_to(ROOT)): sha(p) for p in files(HERE)}}


def artifacts(out):
    suffixes = {'.json', '.wasm', '.wat', '.lisp', '.legacy', '.mjs', '.c', '.dx64fsl', '.sexp', '.refused-wat'}
    return {'numeric/' + str(p.relative_to(out)): sha(p) for p in files(out)
            if (p.relative_to(out).parts[0] != 'driver' or p.name in ('arch-probes.lisp', 'new-inputs.lisp'))
            and p.name not in ('command.json', 'native-read-skips.sexp', 'verification.json')
            and p.suffix in suffixes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('retain', 'verify'))
    for name in ('packet', 'numeric', 'native', 'output'):
        parser.add_argument('--' + name, type=Path, required=name == 'packet')
    args = parser.parse_args()
    packet = args.packet.resolve()
    dependencies = {str((PARENT / n).relative_to(EVIDENCE)): sha(PARENT / n)
                    for n in ('packet.json', 'artifacts.tar.gz', 'deterministic.json', 'source-pins.json', 'dependencies.json')}
    for name in ('2026-09-12-native-census-r7/baseline/build/dx86cl64',
                 '2026-09-16-stage1-1a-r2/native/baseline.image'):
        dependencies[name] = sha(EVIDENCE / name)
    tool_pins = read(PARENT / 'tools.json')
    assert {name: sha(Path(name)) for name in tool_pins} == tool_pins
    previous = read(PARENT / 'deterministic.json')
    if args.mode == 'retain':
        out, native = args.numeric.resolve(), args.native.resolve()
        subprocess.run([sys.executable, HERE / 'check.py', out, native], check=True)
        expected = artifacts(out)
        reused = {k: v for k, v in expected.items() if previous.get(k) == v}
        packet.mkdir()
        for name, value in [('source-pins', pins()), ('dependencies', dependencies),
                            ('tools', tool_pins), ('deterministic', expected), ('reused', reused)]:
            save(packet / (name + '.json'), value)
        with tarfile.open(packet / 'artifacts.tar.gz', 'w:gz', dereference=True) as archive:
            for name in sorted(expected.keys() - reused.keys()):
                path = out / name.removeprefix('numeric/')
                assert sha(path) == expected[name]
                archive.add(path, arcname=name, recursive=False)
        delta.copy_native(native, packet / 'native')
        shutil.copyfile(out / 'generic-summary.json', packet / 'summary.json')
        shutil.copytree(HERE, packet / 'source', ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet / 'development.tar.gz', 'w:gz') as archive:
            for name in read(HERE / 'development.json')['retained']:
                archive.add(Path('/tmp') / name, arcname=name, recursive=False)
        save(packet / 'packet.json', dict(id='STAGE1-BOOTSTRAP-GENERIC-DISPATCH-R1', slot_credit=False,
            review_disposition='NOT_REVIEWED', retained_files=len(expected) - len(reused),
            reused_files=len(reused), files=[dict(path=str(p.relative_to(packet)), sha256=sha(p),
                                                bytes=p.stat().st_size) for p in files(packet)]))
    else:
        assert pins() == read(packet / 'source-pins.json'), 'source pins'
        assert dependencies == read(packet / 'dependencies.json'), 'dependencies'
        assert tool_pins == read(packet / 'tools.json'), 'tools'
        entries = read(packet / 'packet.json')['files']
        assert {r['path'] for r in entries} == {str(p.relative_to(packet)) for p in files(packet) if p != packet / 'packet.json'}
        for row in entries:
            assert sha(packet / row['path']) == row['sha256'], row['path']
        expected, reused = read(packet / 'deterministic.json'), read(packet / 'reused.json')
        assert all(previous.get(k) == v == expected[k] for k, v in reused.items())
        with tarfile.open(packet / 'artifacts.tar.gz') as archive:
            assert set(archive.getnames()) == expected.keys() - reused.keys()
            for entry in archive:
                assert entry.isfile() and hashlib.sha256(archive.extractfile(entry).read()).hexdigest() == expected[entry.name]
        out = args.output.resolve()
        subprocess.run([sys.executable, HERE / 'run.py', out], check=True)
        subprocess.run([sys.executable, HERE / 'check.py', out, packet / 'native'], check=True)
        actual = artifacts(out)
        assert actual == expected, sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        save(out / 'verification.json', dict(status='PASS', deterministic_files=len(actual),
             source_pins=len(pins()), native_reused_by_final_source_hash=True,
             summary=read(out / 'generic-summary.json')))


if __name__ == '__main__':
    main()
