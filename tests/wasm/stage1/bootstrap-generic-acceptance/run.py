"""Install audit 161's reviewed bytes and qualify the integrated dispatch path."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tarfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STORE = ROOT.parent / 'ccl-evidence'
PACKET = STORE / '2026-09-22-stage1-bootstrap-generic-dispatch-r1'
FIXTURE = HERE.parent / 'bootstrap-generic-dispatch'
spec = importlib.util.spec_from_file_location('stack_acceptance', HERE.parent / 'bootstrap-stack-acceptance/run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.PACKET = PACKET
base.PACKET_ID = 'STAGE1-BOOTSTRAP-GENERIC-DISPATCH-R1'
sha, read, save = base.sha, base.read, base.save


def reviewed_files():
    files = {name: path.read_bytes() for name, path in base.reviewed_files().items()}
    pins = {row['path']: row['sha256'] for row in read(PACKET / 'packet.json')['files']}
    archive = PACKET / 'artifacts.tar.gz'
    assert sha(archive) == pins['artifacts.tar.gz']
    assert sha(PACKET / 'deterministic.json') == pins['deterministic.json']
    expected = read(PACKET / 'deterministic.json')
    with tarfile.open(archive) as stream:
        for name in ('collector.c', 'collector-owner.mjs'):
            key = 'numeric/runtime/' + name
            data = stream.extractfile(key).read()
            assert hashlib.sha256(data).hexdigest() == expected[key], key
            files['runtime/wasm32/' + name] = data
    return files


def proposal(source, target):
    """Copy qualified files; do not derive against already integrated sources."""
    files = reviewed_files()
    shutil.copytree(PACKET / 'native/proposal', target)
    for name, reviewed in files.items():
        assert (ROOT / name).read_bytes() == reviewed, name
        if not name.startswith('runtime/'):
            shutil.copyfile(ROOT / name, target / 'files' / name)
    return read(target / 'unit.json')


def qualify_target(out, files):
    work, count = base.materialize(out)
    used = {}
    for source in (ROOT / 'runtime/wasm32').iterdir():
        target = work / 'runtime' / source.name
        if source.is_file() and target.is_file():
            assert source.read_bytes() == target.read_bytes(), source.name
            used[source.name] = sha(source)
            shutil.copyfile(source, target)
    flags = ['--target=wasm32', '-O2', '-nostdlib', '-fno-builtin', '-matomics', '-mbulk-memory',
             '-Wl,--no-entry', '-Wl,--import-memory', '-Wl,--shared-memory',
             '-Wl,--max-memory=2147549184', '-Wl,-z,stack-size=65536',
             '-Wl,--global-base=1048576', '-Wl,--export=collect', '-Wl,--export=__stack_pointer']
    base.command(['/usr/local/opt/llvm/bin/clang', *flags, ROOT/'runtime/wasm32/collector.c',
                  '-o', out/'collector.wasm'], out/'collector-build.log')
    assert sha(out/'collector.wasm') == sha(work/'collector.wasm'), 'integrated collector build'
    shutil.copyfile(out/'collector.wasm', work/'collector.wasm')
    base.command(['/usr/local/bin/node', work/'check.mjs', work, out/'execution.json'], out/'execution.log')
    assert (out/'execution.json').read_bytes() == (work/'execution.json').read_bytes()
    checks = {}
    for script, record in [('istruct-check.mjs', 'istruct-checks.json'),
                           ('population-check.mjs', 'population-checks.json')]:
        base.command(['/usr/local/bin/node', work/script, work/'collector.wasm', out/record], out/(script+'.log'))
        assert (out/record).read_bytes() == (work/record).read_bytes(), record
        checks[record] = sha(out/record)
    owner = work/'owner-check'
    for p in (work/'runtime').glob('*.mjs'):
        shutil.copyfile(p, owner/p.name)
    shutil.copyfile(work/'runtime/collector-owner.mjs', owner/'owner.mjs')
    base.command(['/usr/local/bin/node', owner/'check.mjs', work/'collector.wasm', out/'owner-checks.json'], out/'owner.log')
    assert (out/'owner-checks.json').read_bytes() == (owner/'results.json').read_bytes()
    comparisons = sum(row['comparisons'] for row in read(out/'execution.json')['rows'])
    assert comparisons == read(PACKET/'summary.json')['comparisons'] == 24144
    save(out/'integration.json', dict(status='PASS', files={n:sha(ROOT/n) for n in files},
         runtime=used, collector_binary=sha(out/'collector.wasm'), materialized_artifacts=count,
         execution=sha(out/'execution.json'), owner_checks=read(out/'owner-checks.json')['checks'],
         structural_checks=checks, original_definitions=550, non_nil_witnesses=515,
         comparisons=comparisons, slot_credit=False))
    print('PASS: reviewed integrated bytes, rebuilt collector,', comparisons, 'comparisons and owner/population checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('install', 'verify', 'native', 'recount'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True)
    files = reviewed_files()
    if args.mode == 'install':
        changes = []
        for name, data in files.items():
            target = ROOT/name
            before = sha(target) if target.exists() else None
            digest = hashlib.sha256(data).hexdigest()
            if before != digest:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                changes.append(dict(file=name, before=before, after=sha(target), reviewed=digest))
        save(out/'changes.json', changes)
        print('Installed', len(changes), 'reviewed files')
        return
    for name, data in files.items():
        assert (ROOT/name).read_bytes() == data, name
    for name, digest in read(PACKET/'tools.json').items():
        assert sha(Path(name)) == digest, name
    if args.mode == 'verify':
        qualify_target(out, files)
    elif args.mode == 'native':
        sys.setrecursionlimit(10000)
        sys.path.insert(0, str(FIXTURE))
        spec = importlib.util.spec_from_file_location('generic_native', FIXTURE/'native.py')
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        native.driver.proposal = proposal
        assert native.driver.run(STORE/'macos-u1-inputs',
            STORE/'2026-09-12-native-census-r7/baseline/build/dx86cl64',
            out/'work', out/'native', STORE/'2026-09-16-stage1-1a-r2/native') == 0
    else:
        sys.path.insert(0, str(FIXTURE))
        spec = importlib.util.spec_from_file_location('file_recount', HERE.parent/'bootstrap-lexpr-spread/run.py')
        recount = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recount)
        recount.backend = SimpleNamespace(proposal=proposal, BACKEND='compiler/WASM32/wasm32-backend.lisp')
        # Reuse the file compiler unchanged, with an explicit cohort report
        # that distinguishes the target replacement for COMPUTE-DCODE.
        def report_spec(name, path):
            assert name == 'file_report'
            return importlib.util.spec_from_file_location(name, HERE/'report.py')
        recount.importlib = SimpleNamespace(util=SimpleNamespace(
            spec_from_file_location=report_spec,
            module_from_spec=importlib.util.module_from_spec))
        recount.run(out/'environment')
        summary = read(out/'environment/summary.json')
        summary.pop('original_definitions_executed_reused', None)
        summary.pop('non_nil_witness_reused', None)
        save(out/'recount.json', summary)


if __name__ == '__main__':
    main()
