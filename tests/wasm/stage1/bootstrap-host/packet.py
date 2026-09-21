"""Retain execution growth and target source branches with relative pins."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile

import backend
import run as r

spec = importlib.util.spec_from_file_location('library_packet', r.HERE.parent / 'bootstrap-library/packet.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
sha, read, files, deterministic = prior.sha, prior.read, prior.files, prior.deterministic
ACCEPTED = '2026-09-21-stage1-bootstrap-witnesses-accepted'
ID = 'STAGE1-BOOTSTRAP-HOST-R1'


def pins():
    result = prior.pins()
    manifest = read(backend.PACKET / 'unit.json')
    for row in manifest['added'] + manifest['modified']:
        result[row['path']] = sha(r.ROOT / row['path'])
    for name in ('tests/wasm/stage1/bootstrap-witnesses-acceptance/run.py',
                 'tests/wasm/stage1/bootstrap-witnesses-acceptance/execute.py',
                 'doc/WASM/tools/r6_registration.py', 'xdump/faslenv.lisp'):
        result[name] = sha(r.ROOT / name)
    path = r.HERE.parent / 'bootstrap-library/packet.py'
    result[str(path.relative_to(r.ROOT))] = sha(path)
    for name in ('level-1/level-1.lisp', 'tests/wasm/stage1/bootstrap-core/probe.py'):
        result[name] = sha(r.ROOT/name)
    return result


def dependencies():
    result = prior.dependencies()
    paths = list(files(backend.PACKET))
    paths += [r.EVIDENCE / ACCEPTED / n for n in
              ('packet.json', 'native/run.json', 'native/registered-fasls.json',
               'native/registered-snapshot.json', 'execution/integration.json',
               'execution/owner-check/results.json',
               'integrated/runtime/wasm32/collector.c',
               'integrated/runtime/wasm32/collector-owner.mjs')]
    paths += [r.EVIDENCE / '2026-09-21-stage1-bootstrap-carry-r1' / n for n in ('packet.json', 'execution/execution-frontier.json', 'execution/member-witnesses.json', 'execution/compiled/native.json')]
    paths += [r.EVIDENCE / '2026-09-21-stage1-bootstrap-inputs-r1' / n for n in ('packet.json', 'execution/execution-frontier.json', 'execution/compiled/native.json')]
    paths.append(r.EVIDENCE / '2026-09-21-stage1-bootstrap-carry-r1/execution/compiled/worklist.sexp')
    for path in paths:
        result[str(path.relative_to(r.EVIDENCE))] = sha(path)
    return result


def native_check(path):
    import native
    report = read(path / 'run.json')
    assert report['status'] == 'PASS'
    assert report['registered_tests']['passed'] == 21843
    assert report['r6']['identical'] == 146 and report['restored_fasls'] == 164
    assert report['source_restored'] and report['r6']['native_state_equal']
    assert report['r6']['existing_target_module_profiles'] == 17
    for source, _ in native.source_pairs():
        result = read(path / (Path(source).stem + '-comparison.json'))
        assert result['status'] == 'PASS'
    assert (path / 'proposal/files' / backend.BACKEND).read_text() == backend.generate()
    for name, text in backend.source_files(r.ROOT).items():
        assert (path / 'proposal/files' / name).read_text() == text
    arch = 'compiler/WASM32/wasm32-arch.lisp'
    assert (path / 'proposal/files' / arch).read_text() == (r.ROOT / arch).read_text() + (r.HERE / 'io-constants.lisp').read_text()


def source_check(out):
    for name in ('compile.lisp', 'cases.lisp', 'execute.lisp', 'probes.lisp',
                 'controls.lisp', 'whole-file.lisp', 'witnesses.lisp', 'inputs.lisp',
                 'foreign-scan.lisp', 'w32-os.lisp', 'os-probes.lisp'):
        actual = out / ('compiled/source' if name == 'compile.lisp' else 'driver') / name
        assert actual.read_bytes() == r.fixture(name).read_bytes(), name
    for name in ('check.mjs', 'install.mjs'):
        assert (out / name).read_bytes() == (r.HERE / name).read_bytes(), name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('retain', 'verify'))
    for name in ('packet', 'execution', 'native-run', 'readers', 'output'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    packet = args.packet.resolve()
    if args.mode == 'retain':
        out, native = args.execution.resolve(), args.native_run.resolve()
        native_check(native)
        source_check(out)
        assert read(out / 'summary.json')['status'] == 'PASS'
        matrix = read(args.readers.resolve() / 'readers.json')
        assert len(matrix['rows']) == 204 and all(row['equal'] for row in matrix['rows'])
        packet.mkdir()
        shutil.copytree(args.readers.resolve(), packet / 'readers')
        for name, data in [('source-pins', pins()), ('dependencies', dependencies()),
                           ('tools', prior.tools()), ('deterministic', deterministic(out))]:
            r.save(packet / (name + '.json'), data)
        for f in files(out):
            rel = f.relative_to(out)
            if prior.keep(rel):
                dest = packet / 'execution' / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, dest)
        omitted = {}
        for f in files(native):
            rel = f.relative_to(native)
            if f.name in ('baseline.image', 'baseline-fasls.tar.gz', 'registered.image'):
                omitted[str(rel)] = sha(f)
                continue
            dest = packet / 'native' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, dest)
        r.save(packet / 'omitted-images.json', omitted)
        shutil.copytree(r.HERE, packet / 'source', ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet / 'development.tar.gz', 'w:gz') as tar:
            for name in read(r.HERE / 'development.json')['retained']:
                tar.add(Path('/tmp') / name, arcname=name, recursive=False)
        r.save(packet / 'packet.json', dict(id=ID, slot_credit=False, review_disposition='NOT_REVIEWED',
               files=[dict(path=str(f.relative_to(packet)), sha256=sha(f), bytes=f.stat().st_size)
                      for f in files(packet)]))
    else:
        assert pins() == read(packet / 'source-pins.json'), 'source pins'
        assert dependencies() == read(packet / 'dependencies.json'), 'dependencies'
        assert prior.tools() == read(packet / 'tools.json'), 'tools'
        entries = read(packet / 'packet.json')['files']
        assert {r['path'] for r in entries} == {str(f.relative_to(packet)) for f in files(packet) if f.name != 'packet.json'}
        for row in entries:
            assert sha(packet / row['path']) == row['sha256'], row['path']
        native_check(packet / 'native')
        out = args.output.resolve()
        r.run(out)
        # Reader comparisons use a fresh pristine source restored by compile.py.
        import readers
        readers.replay(r.EVIDENCE, out / 'compiled/proposal/files', out / 'reader-replay')
        for name in ('readers.json', 'summary.json', 'substitutions.json'):
            assert read(out / 'reader-replay' / name) == read(packet / 'readers' / name), name
        source_check(out)
        actual, expected = {k:v for k,v in deterministic(out).items() if not k.startswith('reader-replay/')}, read(packet / 'deterministic.json')
        assert actual == expected, sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        r.save(out / 'verification.json', dict(status='PASS', deterministic_files=len(actual),
               source_pins=len(pins()), summary=read(out / 'summary.json')))


if __name__ == '__main__':
    main()
