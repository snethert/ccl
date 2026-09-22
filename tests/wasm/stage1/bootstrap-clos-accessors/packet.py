"""Retain this recipe delta; reuse the unchanged compiler's native qualification."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys, tarfile
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVIDENCE = ROOT.parent / 'ccl-evidence'
PARENT = EVIDENCE / '2026-09-22-stage1-bootstrap-lexpr-spread-r1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
def save(p, value):
    p.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
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
                         'source-pins.json', 'dependencies.json', 'tools.json', 'native/run.json')}
def tools():
    prior = read(PARENT / 'tools.json')
    assert {name: sha(Path(name)) for name in prior} == prior
    return prior

def source_check(out):
    for source in HERE.glob('*.lisp'):
        assert (out / 'driver' / source.name).read_bytes() == source.read_bytes(), source.name
    assert (out / 'check.mjs').read_bytes() == (HERE / 'check.mjs').read_bytes()
    report = read(PARENT / 'native/run.json')
    assert report['status'] == 'PASS' and report['registered_tests']['passed'] == 21843
    assert report['restored_fasls'] == 164 and report['r6']['identical'] == 140
    subprocess.run([sys.executable, HERE / 'summary.py', out], check=True)

def deterministic(out):
    suffixes = {'.json', '.wasm', '.wat', '.lisp', '.legacy', '.mjs', '.c', '.dx64fsl', '.sexp', '.refused-wat'}
    return {'numeric/'+str(p.relative_to(out)): sha(p) for p in files(out)
            if p.relative_to(out).parts[0] != 'driver'
            and p.name not in ('command.json', 'native-read-skips.sexp', 'verification.json')
            and p.suffix in suffixes}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('retain', 'verify'))
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--execution', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    packet = args.packet.resolve()
    if args.mode == 'retain':
        out = args.execution.resolve()
        source_check(out)
        assert read(out / 'clos-controls.json')['status'] == 'PASS'
        expected = deterministic(out)
        previous = read(PARENT / 'deterministic.json')
        reused = {k: v for k, v in expected.items() if previous.get(k) == v}
        packet.mkdir()
        for name, value in [('source-pins', pins()), ('dependencies', dependencies()),
                            ('tools', tools()), ('deterministic', expected), ('reused', reused)]:
            save(packet / (name+'.json'), value)
        shutil.copyfile(out / 'summary.json', packet / 'summary.json')
        save(packet / 'native-reuse.json', dict(packet=str(PARENT.relative_to(EVIDENCE)),
             report_sha256=sha(PARENT / 'native/run.json'), reason='Exact compiler, arch and CCL source equality asserted by summary.py. Recipes only.'))
        with tarfile.open(packet / 'artifacts.tar.gz', 'w:gz', dereference=True) as archive:
            for name in expected.keys()-reused.keys():
                path = out / name.removeprefix('numeric/')
                assert sha(path) == expected[name]
                archive.add(path, arcname=name, recursive=False)
        shutil.copytree(HERE, packet / 'source', ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet / 'development.tar.gz', 'w:gz') as archive:
            for name in read(HERE / 'development.json')['retained']:
                archive.add(Path('/tmp') / name, arcname=name, recursive=False)
        save(packet / 'packet.json', dict(id='STAGE1-BOOTSTRAP-CLOS-ACCESSORS-R1',
             slot_credit=False, review_disposition='NOT_REVIEWED',
             retained_files=len(expected)-len(reused), reused_files=len(reused),
             files=[dict(path=str(p.relative_to(packet)), sha256=sha(p), bytes=p.stat().st_size) for p in files(packet)]))
    else:
        assert pins() == read(packet / 'source-pins.json')
        assert dependencies() == read(packet / 'dependencies.json')
        assert tools() == read(packet / 'tools.json')
        entries = read(packet / 'packet.json')['files']
        assert {r['path'] for r in entries} == {str(p.relative_to(packet)) for p in files(packet) if p != packet / 'packet.json'}
        for row in entries:
            assert sha(packet / row['path']) == row['sha256'], row['path']
        expected = read(packet / 'deterministic.json')
        reused = read(packet / 'reused.json')
        previous = read(PARENT / 'deterministic.json')
        assert all(previous.get(k) == v == expected[k] for k, v in reused.items())
        with tarfile.open(packet / 'artifacts.tar.gz') as archive:
            assert set(archive.getnames()) == expected.keys()-reused.keys()
            for entry in archive:
                assert entry.isfile() and hashlib.sha256(archive.extractfile(entry).read()).hexdigest() == expected[entry.name]
        out = args.output.resolve()
        subprocess.run([sys.executable, HERE / 'run.py', out], check=True)
        subprocess.run([sys.executable, HERE / 'controls.py', out], check=True)
        source_check(out)
        actual = deterministic(out)
        assert actual == expected, sorted(k for k in actual.keys()|expected.keys() if actual.get(k) != expected.get(k))
        save(out / 'verification.json', dict(status='PASS', deterministic_files=len(actual),
             source_pins=len(pins()), native_reused_by_final_source_hash=True, summary=read(out / 'summary.json')))
if __name__ == '__main__':
    main()
