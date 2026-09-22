"""Retain one delta and replay it without rebuilding unchanged native inputs."""
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
EVIDENCE = ROOT.parent / 'ccl-evidence'
PARENT = EVIDENCE / '2026-09-22-stage1-bootstrap-clos-accessors-r1'
ID = 'STAGE1-BOOTSTRAP-NUMERIC-DISPATCH-R1'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(path.read_text())

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def files(path):
    return sorted(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)

def pins():
    prior = read(PARENT / 'source-pins.json')
    for name, digest in prior.items():
        assert sha(ROOT / name) == digest, name
    return {**prior, **{str(p.relative_to(ROOT)): sha(p) for p in files(HERE)}}

def dependencies():
    return {str((PARENT / name).relative_to(EVIDENCE)): sha(PARENT / name)
            for name in ('packet.json', 'artifacts.tar.gz', 'deterministic.json',
                         'source-pins.json', 'dependencies.json', 'tools.json')}

def tools():
    result = read(PARENT / 'tools.json')
    assert {name: sha(Path(name)) for name in result} == result
    return result

def reports(numeric, environment, native):
    subprocess.run([sys.executable, HERE / 'summary.py', numeric, environment, native], check=True)
    subprocess.run([sys.executable, HERE.parent / 'bootstrap-lexpr-spread/frontier.py',
                    environment, numeric], check=True)

def deterministic(numeric, environment):
    suffixes = {'.json', '.wasm', '.wat', '.lisp', '.legacy', '.mjs', '.c', '.dx64fsl', '.sexp', '.refused-wat'}
    result = {'numeric/' + str(p.relative_to(numeric)): sha(p) for p in files(numeric)
              if p.relative_to(numeric).parts[0] != 'driver'
              and p.name not in ('command.json', 'native-read-skips.sexp', 'verification.json')
              and p.suffix in suffixes}
    # Bind every emitted module without copying the repetitive whole-worklist WAT.
    save(environment / 'module-digests.json',
         {str(p.relative_to(environment)): sha(p) for p in sorted((environment / 'files').rglob('*.wat'))})
    for name in ('worklist.json', 'results.json', 'summary.json', 'cohort-changes.json',
                 'additional-definitions.json', 'audit156-cohort.json', 'controls.json',
                 'inputs.json', 'module-digests.json'):
        result['environment/' + name] = sha(environment / name)
    for directory in ('controls', 'files/l0-numbers', 'files/l0-float', 'files/l0-bignum32', 'files/l1-dcode'):
        for p in files(environment / directory):
            if p.suffix in ('.json', '.wat', '.wasm'):
                result['environment/' + str(p.relative_to(environment))] = sha(p)
    return result

def copy_native(source, destination):
    omitted = {}
    for p in files(source):
        rel = p.relative_to(source)
        if p.name in ('baseline.image', 'registered.image', 'baseline-fasls.tar.gz'):
            omitted[str(rel)] = sha(p)
            continue
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    save(destination / 'omitted-images.json', omitted)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('retain', 'verify'))
    parser.add_argument('--packet', type=Path, required=True)
    for name in ('numeric', 'environment', 'native', 'output'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    packet = args.packet.resolve()
    if args.mode == 'retain':
        numeric, environment, native = (p.resolve() for p in (args.numeric, args.environment, args.native))
        reports(numeric, environment, native)
        expected = deterministic(numeric, environment)
        previous = read(PARENT / 'deterministic.json')
        reused = {k: v for k, v in expected.items() if previous.get(k) == v}
        packet.mkdir()
        for name, value in (('source-pins', pins()), ('dependencies', dependencies()),
                            ('tools', tools()), ('deterministic', expected), ('reused', reused)):
            save(packet / (name + '.json'), value)
        shutil.copyfile(numeric / 'summary.json', packet / 'summary.json')
        with tarfile.open(packet / 'artifacts.tar.gz', 'w:gz', dereference=True) as archive:
            for name in sorted(expected.keys() - reused.keys()):
                group, relative = name.split('/', 1)
                path = (numeric if group == 'numeric' else environment) / relative
                assert sha(path) == expected[name]
                archive.add(path, arcname=name, recursive=False)
        copy_native(native, packet / 'native')
        shutil.copytree(HERE, packet / 'source', ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet / 'development.tar.gz', 'w:gz') as archive:
            for name in read(HERE / 'development.json')['retained']:
                archive.add(Path('/tmp') / name, arcname=name, recursive=False)
        save(packet / 'packet.json', dict(id=ID, slot_credit=False, review_disposition='NOT_REVIEWED',
             retained_files=len(expected) - len(reused), reused_files=len(reused),
             files=[dict(path=str(p.relative_to(packet)), sha256=sha(p), bytes=p.stat().st_size) for p in files(packet)]))
    else:
        assert pins() == read(packet / 'source-pins.json'), 'source pins'
        assert dependencies() == read(packet / 'dependencies.json'), 'dependencies'
        assert tools() == read(packet / 'tools.json'), 'tools'
        entries = read(packet / 'packet.json')['files']
        assert {r['path'] for r in entries} == {str(p.relative_to(packet)) for p in files(packet) if p != packet / 'packet.json'}
        for row in entries:
            assert sha(packet / row['path']) == row['sha256'], row['path']
        expected, reused = read(packet / 'deterministic.json'), read(packet / 'reused.json')
        previous = read(PARENT / 'deterministic.json')
        assert all(previous.get(k) == v == expected[k] for k, v in reused.items())
        with tarfile.open(packet / 'artifacts.tar.gz') as archive:
            assert set(archive.getnames()) == expected.keys() - reused.keys()
            for entry in archive:
                assert entry.isfile() and hashlib.sha256(archive.extractfile(entry).read()).hexdigest() == expected[entry.name]
        out = args.output.resolve()
        out.mkdir()
        numeric, environment = out / 'numeric', out / 'environment'
        subprocess.run([sys.executable, HERE / 'run.py', numeric], check=True)
        subprocess.run([sys.executable, HERE / 'recount.py', environment], check=True)
        reports(numeric, environment, packet / 'native')
        actual = deterministic(numeric, environment)
        assert actual == expected, sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        save(out / 'verification.json', dict(status='PASS', deterministic_files=len(actual),
             source_pins=len(pins()), native_reused_by_final_source_hash=True,
             summary=read(numeric / 'summary.json')))

if __name__ == '__main__':
    main()
