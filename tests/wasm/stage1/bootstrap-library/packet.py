"""Retain and replay one whole-file compiler proposal; paths are checkout-relative."""
import argparse, hashlib, json, shutil, subprocess, sys, tarfile
from pathlib import Path
import run as r
from backend import generate, source_files
ID = 'STAGE1-BOOTSTRAP-LIBRARY-R1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)

def pins():
    paths = {p for p in r.HERE.iterdir() if p.is_file()}
    for name in ('level-0', 'level-1', 'tests/wasm/stage1/constants',
                 'tests/wasm/stage1/registration', 'tests/wasm/stage1/bootstrap-values',
                 'tests/wasm/stage1/bootstrap-frontend', 'tests/wasm/stage1/bootstrap-core', 'tests/wasm/stage1/bootstrap-core-acceptance', 'runtime/wasm32'):
        paths.update(p for p in (r.ROOT / name).iterdir()
                     if p.is_file() and (name not in ('level-0', 'level-1') or p.suffix == '.lisp'))
    paths.update(r.ROOT / p for p in (
        'compiler/WASM32/wasm32-backend.lisp', 'compiler/WASM32/wasm32-arch.lisp',
        'xdump/xwasm32-fasload.lisp','compiler/nx0.lisp', 'compiler/nx1.lisp', 'compiler/nxenv.lisp',
        'compiler/lambda-list.lisp', 'compiler/X86/x862.lisp', 'xdump/hashenv.lisp',
        'library/lispequ.lisp', 'lib/systems.lisp', 'lib/compile-ccl.lisp',
        'doc/WASM/contracts/wasm32-layout.v1.json',
        'tests/wasm/stage1/float-calls/class-shapes.lisp',
        'tests/wasm/native-census/observer.lisp', 'tests/wasm/native-baseline/tests.lisp'))
    return {str(p.relative_to(r.ROOT)): sha(p) for p in sorted(paths)}

def dependencies():
    paths = ['2026-09-21-stage1-population-pushnew-r1/execution/' + name
             for name in ('eql.wasm', 'eql-adapter.wat')]
    paths += [str(p.relative_to(r.EVIDENCE)) for p in sorted(
        (r.EVIDENCE / '2026-09-21-stage1-bootstrap-values-r1/execution/compiled').glob('*.legacy'))]
    paths += ['macos-u1-inputs/' + name for name in ('source.tar', 'bootstrap.tar.gz', 'tests.tar')]
    paths += ['2026-09-16-stage1-1a-r2/native/' + name for name in
              ('run.json', 'baseline.image', 'baseline-fasls.tar.gz')]
    paths += ['2026-09-12-native-census-r7/baseline/build/dx86cl64',
              '2026-09-21-stage1-bootstrap-core-accepted/packet.json']
    return {p: sha(r.EVIDENCE / p) for p in paths}

def tools():
    return {str(p): sha(p) for p in map(Path, (
        '/usr/local/bin/node', '/usr/local/bin/wat2wasm', '/usr/local/opt/llvm/bin/clang'))}

def keep(path):
    return path.parts[0] != 'driver' and path.name != 'command.json'

def deterministic(root):
    suffixes = {'.json', '.wasm', '.wat', '.lisp', '.legacy', '.mjs', '.c', '.dx64fsl', '.sexp', '.refused-wat'}
    return {str(p.relative_to(root)): sha(p) for p in files(root)
            if keep(p.relative_to(root)) and p.name != 'native-read-skips.sexp' and p.suffix in suffixes}

def assert_native(root):
    x = read(root / 'run.json')
    assert x['status'] == 'PASS' and x['registered_tests']['passed'] == 21843
    assert x['r6']['identical'] == 158 and x['restored_fasls'] == 164 and x['source_restored']
    assert x['r6']['native_state_equal'] and x['r6']['existing_architectures'] == 5
    assert x['r6']['existing_target_module_profiles'] == 17
    assert sha(root / 'proposal/files/compiler/WASM32/wasm32-backend.lisp') == hashlib.sha256(generate().encode()).hexdigest()
    for name, text in source_files(r.ROOT).items():
        assert (root / 'proposal/files' / name).read_text() == text, name
    comparisons = [read(root / (n + '-comparison.json')) for n in ('l0-def', 'l0-pred', 'l0-utils', 'l0-symbol')]
    assert all(x['status'] == 'PASS' for x in comparisons)
    assert sum(x['functions'] for x in comparisons) == 169

def manifest(root):
    r.save(root / 'packet.json', dict(id=ID, slot_credit=False, review_disposition='NOT_REVIEWED',
        files=[dict(path=str(p.relative_to(root)), sha256=sha(p), bytes=p.stat().st_size)
               for p in files(root) if p.name != 'packet.json']))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['retain', 'verify'])
    for n in ('packet', 'execution', 'native-run', 'native-test-run', 'readers', 'output'):
        parser.add_argument('--' + n, type=Path)
    parser.add_argument('--native', action='store_true')
    a = parser.parse_args(); p = a.packet.resolve()
    if a.mode == 'retain':
        x = a.execution.resolve(); n = a.native_run.resolve(); assert_native(n)
        assert read(x / 'summary.json')['status'] == 'PASS'
        p.mkdir()
        for name, data in [('source-pins', pins()), ('dependencies', dependencies()), ('tools', tools()), ('deterministic', deterministic(x))]:
            r.save(p / (name + '.json'), data)
        for f in files(x):
            rel = f.relative_to(x)
            if keep(rel):
                dst = p / 'execution' / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst)
        tests=a.native_test_run.resolve()
        test_report=read(tests/'run.json')
        assert test_report['registered_tests']['passed']==21843 and test_report['status']=='PASS'
        assert sha(tests/'run.json')==read(n/'run.json')['registered_tests_reuse']['run_sha256']
        assert read(tests/'registered-fasls.json')==read(n/'registered-fasls.json')
        shutil.copytree(tests/'registered-tests',p/'native-test-execution')
        for name in ('run.json','registered-fasls.json','registered-snapshot.json','commands.json','registered-tests.log'):
            shutil.copy(tests/name,p/('native-test-'+name))
        shutil.copytree(a.readers.resolve(),p/'readers')
        matrix=read(p/'readers/readers.json')
        assert matrix['status']=='PASS' and len(matrix['rows'])==17
        assert all(row['equal'] for row in matrix['rows'])
        assert read(p/'readers/summary.json')['source_sha256']==sha(n/'proposal/files/level-0/l0-symbol.lisp')
        reused = {}
        for f in files(n):
            rel = f.relative_to(n)
            if f.name in ('baseline.image', 'baseline-fasls.tar.gz', 'registered.image'):
                reused[str(rel)] = dict(sha256=sha(f), bytes=f.stat().st_size); continue
            dst = p / 'native' / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst)
        r.save(p / 'native-omitted-images.json', reused)
        for name in ('README.md', 'development.json'):
            shutil.copy(r.HERE / name, p / name)
        shutil.copytree(r.HERE, p / 'source', ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(p / 'development.tar.gz', 'w:gz') as tar:
            for name in read(r.HERE / 'development.json')['retained']:
                tar.add(Path('/tmp') / name, arcname=name, recursive=False)
        manifest(p)
    else:
        assert pins() == read(p / 'source-pins.json'), 'source pins'
        assert dependencies() == read(p / 'dependencies.json'), 'reused dependency pins'
        assert tools() == read(p / 'tools.json'), 'tool pins'
        listed = read(p / 'packet.json')['files']
        assert {x['path'] for x in listed} == {str(f.relative_to(p)) for f in files(p) if f.name != 'packet.json'}
        for row in listed: assert sha(p / row['path']) == row['sha256'], row['path']
        assert_native(p / 'native')
        out = a.output.resolve(); r.run(out)
        actual = deterministic(out); expected = read(p / 'deterministic.json')
        assert actual == expected, sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        if a.native:
            n = out / 'native-replay'
            subprocess.run([sys.executable, r.HERE / 'native.py', '--evidence', r.EVIDENCE,
                            '--work', out / 'native-work', '--output', n], check=True)
            assert_native(n)
        result = dict(status='PASS', deterministic_files=len(actual), source_pins=len(pins()),
                      summary=read(out / 'summary.json'), native_rebuilt=a.native)
        r.save(out / 'verification.json', result)
        print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
