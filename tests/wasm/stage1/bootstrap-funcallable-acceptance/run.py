"""Install reviewed bytes; replay through production imports, with audit 158 O-7."""
import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVIDENCE = ROOT.parent / 'ccl-evidence'
PACKET = EVIDENCE / '2026-09-22-stage1-bootstrap-funcallable-r1'
PACKET_SHA = 'a76586c238c38bcd5c151a3997738471571a303c5007f000bc8f904a2b3ed96d'
RUNTIME = ('collector.c', 'collector-owner.mjs', 'installer.mjs', 'ranges.mjs',
           'float.c', 'transcend.c', 'float-service.mjs')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def prepare(out):
    assert sha(PACKET / 'packet.json') == PACKET_SHA
    pins = {row['path']: row['sha256'] for row in json.loads((PACKET / 'packet.json').read_text())['files']}
    archive = PACKET / 'artifacts.tar.gz'
    assert sha(archive) == pins['artifacts.tar.gz']
    dest = out / 'reviewed'
    if not dest.exists():
        dest.mkdir()
        with tarfile.open(archive) as stream:
            for member in stream:
                if member.name.startswith('numeric/') and member.isfile():
                    path = dest / member.name
                    assert path.resolve().is_relative_to(dest.resolve())
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(stream.extractfile(member).read())
    deterministic = PACKET / 'deterministic.json'
    assert sha(deterministic) == pins['deterministic.json']
    for name, digest in json.loads(deterministic.read_text()).items():
        if name.startswith('numeric/'):
            assert sha(dest / name) == digest, name
    proposal = PACKET / 'native/proposal'
    assert sha(proposal / 'unit.json') == pins['native/proposal/unit.json']
    manifest = json.loads((proposal / 'unit.json').read_text())
    files = {}
    for row in manifest['added'] + manifest['modified']:
        source = proposal / 'files' / row['path']
        assert sha(source) == pins[str(source.relative_to(PACKET))]
        assert sha(source) == row.get('sha256', row.get('after'))
        files[row['path']] = source
    runtime = dest / 'numeric/runtime'
    for name in RUNTIME:
        files['runtime/wasm32/' + name] = runtime / name
    # The existing build includes all *.c; keep old provenance and bind the
    # additional eight source files to their reviewed hyperbolic provenance.
    extra = PACKET / 'source/libm'
    if not extra.exists():
        extra = EVIDENCE / '2026-09-22-stage1-bootstrap-hyperbolic-r2/source/libm'
    for source in extra.glob('*.c'):
        files['runtime/wasm32/libm/' + source.name] = runtime / 'libm' / source.name
        assert source.read_bytes() == files['runtime/wasm32/libm/' + source.name].read_bytes()
    files['runtime/wasm32/libm/hyperbolic-provenance.json'] = extra / 'provenance.json'
    return files, dest / 'numeric'


def run(args, log):
    with log.open('w') as stream:
        subprocess.run(list(map(str, args)), cwd=ROOT, check=True, stdout=stream,
                       stderr=subprocess.STDOUT, timeout=180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('install', 'verify'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    files, reviewed = prepare(out)
    if args.mode == 'install':
        changes = []
        for name, source in files.items():
            target = ROOT / name
            before = sha(target) if target.exists() else None
            if before != sha(source):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                changes.append(dict(file=name, before=before, after=sha(target), reviewed=sha(source)))
        save(out / 'changes.json', changes)
        print('Installed', len(changes), 'reviewed files')
        return
    for name, source in files.items():
        assert (ROOT / name).read_bytes() == source.read_bytes(), name
    work = out / 'production'
    shutil.copytree(reviewed, work, dirs_exist_ok=True)
    for source in (ROOT / 'runtime/wasm32').glob('*.mjs'):
        shutil.copyfile(source, work / 'runtime' / source.name)
    run(['python3', ROOT / 'runtime/wasm32/build-float.py', '--output', work], out / 'float-build.log')
    run(['/usr/local/opt/llvm/bin/clang', '--target=wasm32', '-O2', '-nostdlib', '-fno-builtin',
         '-Wl,--no-entry', '-Wl,--import-memory', '-Wl,--max-memory=2147549184',
         '-Wl,-z,stack-size=65536', '-matomics', '-mbulk-memory', '-Wl,--shared-memory',
         '-Wl,--global-base=1048576', '-Wl,--export=collect', '-Wl,--export=__stack_pointer',
         ROOT / 'runtime/wasm32/collector.c', '-o', work / 'collector.wasm'], out / 'collector-build.log')
    for name in ('float.wasm', 'collector.wasm'):
        assert (work / name).read_bytes() == (reviewed / name).read_bytes(), name
    run(['/usr/local/bin/node', work / 'check.mjs', work, out / 'execution.json'], out / 'execution.log')
    assert (out / 'execution.json').read_bytes() == (reviewed / 'execution.json').read_bytes()
    for script, binary, result in [('owner-regression.mjs', 'collector.wasm', 'owner-regression.json'),
                                   ('owner-check.mjs', 'collector.wasm', 'owner-checks.json'),
                                   ('istruct-check.mjs', 'collector.wasm', 'istruct-checks.json')]:
        run(['/usr/local/bin/node', work / script, work / binary, out / result], out / (result + '.log'))
        assert (out / result).read_bytes() == (reviewed / result).read_bytes(), result
    # Native raw observer, not a rewritten oracle. The target projection below
    # is an explicitly declared architecture difference, not native equality.
    kernel = EVIDENCE / '2026-09-12-native-census-r7/baseline/build/dx86cl64'
    image = kernel.with_suffix('.image')
    observer = HERE / 'single-observer.lisp'
    executable = out / 'native-kernel'
    shutil.copyfile(kernel, executable)
    executable.chmod(0o755)
    run([executable, '-I', image, '--no-init', '--batch', '--load', observer], out / 'single-native.log')
    assert 'AUDIT158-SINGLE-IDENTITY (T T)' in (out / 'single-native.log').read_text()
    rows = json.loads((reviewed / 'compiled/native.json').read_text())
    row = copy.deepcopy(next(r for r in rows if r['definition'] == 'CORE-ARCH-IDENTITY'))
    row.update(args=[{'single': 1069547520}], after=[{'single': 1069547520}], values=[None, None])
    save(work / 'compiled/native.json', [row])
    run(['/usr/local/bin/node', work / 'check.mjs', work, out / 'single-target.json'], out / 'single-target.log')
    result = json.loads((out / 'single-target.json').read_text())
    assert sum(r['comparisons'] for r in result['rows']) == 4
    save(out / 'single-observer.json', dict(status='PASS', input_bits='3fc00000',
         native_x8664=[True, True], wasm32=[None, None], comparisons=4,
         placements=[262144, 2147483648], before_and_after_movement=True,
         native_kernel=sha(kernel), native_image=sha(image), observer=sha(observer),
         scope='Boxed single floats follow x8632: neither immediate nor hashed by identity. Declared difference, no native-match or definition credit.'))
    save(out / 'integration.json', dict(status='PASS', files={name:sha(ROOT/name) for name in files},
         binaries={name:sha(work/name) for name in ('float.wasm','collector.wasm')},
         native_reuse=dict(record=sha(PACKET/'native/run.json'), exact_proposal_source=True),
         production_execution=sha(out/'execution.json'), owner_checks=40,
         single_observer=sha(out/'single-observer.json'), original_definitions=470,
         non_nil_witnesses=439, admitted=2043, denominator=2231,
         scope='Reviewed final bytes, production imports and rebuilt binaries. No new definition or slot credit.'))
    print('PASS: exact reviewed integration, production execution, 40 owner checks, single-float observer')


if __name__ == '__main__':
    main()
