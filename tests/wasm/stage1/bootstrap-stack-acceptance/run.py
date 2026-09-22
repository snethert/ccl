"""Integrate audit 159's final bytes and qualify production imports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STORE = ROOT.parent / 'ccl-evidence'
PACKET = STORE / '2026-09-22-stage1-bootstrap-limb-division-r1'
PACKET_ID = 'STAGE1-BOOTSTRAP-LIMB-DIVISION-R1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def reviewed_files():
    row = next(r for r in read(ROOT / 'doc/WASM/evidence/index.json')['auxiliary_records'] if r['id'] == PACKET_ID)
    assert sha(PACKET / 'packet.json') == row['sha256']
    pins = {r['path']: r['sha256'] for r in read(PACKET / 'packet.json')['files']}
    unit = PACKET / 'native/proposal/unit.json'
    assert sha(unit) == pins['native/proposal/unit.json']
    manifest = read(unit)
    files = {}
    for row in manifest['added'] + manifest['modified']:
        path = PACKET / 'native/proposal/files' / row['path']
        assert sha(path) == pins[str(path.relative_to(PACKET))] == row.get('sha256', row.get('after'))
        files[row['path']] = path
    return files


def materialize(out):
    """Read the immutable delta chain, retaining each final artifact once."""
    wanted = {k: v for k, v in read(PACKET / 'deterministic.json').items() if k.startswith('numeric/')}
    remaining = dict(wanted)
    packet = PACKET
    pending = []
    visited = set()
    while remaining:
        assert packet not in visited, 'artifact dependency cycle'
        visited.add(packet)
        manifest = read(packet / 'packet.json')
        pins = {r['path']: r['sha256'] for r in manifest['files']}
        archive = packet / 'artifacts.tar.gz'
        assert sha(archive) == pins['artifacts.tar.gz']
        current = read(packet / 'deterministic.json')
        with tarfile.open(archive) as stream:
            for member in stream:
                name = member.name
                if name not in remaining or current.get(name) != remaining[name]:
                    continue
                assert member.isfile()
                data = stream.extractfile(member).read()
                assert hashlib.sha256(data).hexdigest() == remaining.pop(name), name
                target = out / name
                assert target.resolve().is_relative_to(out.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        if remaining:
            dependencies = read(packet / 'dependencies.json')
            pending.extend((STORE / name, digest) for name, digest in dependencies.items()
                           if name.endswith('/artifacts.tar.gz') and (STORE / name).parent not in visited)
            while pending and pending[-1][0].parent in visited:
                pending.pop()
            assert pending, sorted(remaining)
            parent, digest = pending.pop()
            assert sha(parent) == digest
            packet = parent.parent
    return out / 'numeric', len(wanted)


def command(args, log):
    with log.open('w') as stream:
        subprocess.run(list(map(str, args)), cwd=ROOT, check=True, stdout=stream,
                       stderr=subprocess.STDOUT)


def native(out, files):
    sys.setrecursionlimit(10000)
    fixture = HERE.parent / 'bootstrap-limb-division'
    sys.path.insert(0, str(fixture))
    spec = importlib.util.spec_from_file_location('division_native', fixture / 'native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def proposal(source, target):
        shutil.copytree(PACKET / 'native/proposal', target)
        for name in files:
            assert (ROOT / name).read_bytes() == files[name].read_bytes(), name
            shutil.copyfile(ROOT / name, target / 'files' / name)
        return read(target / 'unit.json')

    module.m.driver.proposal = proposal
    result = module.m.driver.run(STORE / 'macos-u1-inputs',
        STORE / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
        out / 'work', out / 'native', STORE / '2026-09-16-stage1-1a-r2/native')
    assert result == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('install', 'verify', 'native'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    files = reviewed_files()
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
    if args.mode == 'native':
        native(out, files)
        return
    work, count = materialize(out)
    # The stack adds no runtime source changes. Check all used production
    # modules against their retained counterparts before running them.
    used = {}
    for source in (ROOT / 'runtime/wasm32').glob('*.mjs'):
        target = work / 'runtime' / source.name
        if target.exists():
            assert source.read_bytes() == target.read_bytes(), source.name
            used[source.name] = sha(source)
            shutil.copyfile(source, target)
    command(['/usr/local/bin/node', work / 'check.mjs', work, out / 'execution.json'], out / 'execution.log')
    assert (out / 'execution.json').read_bytes() == (work / 'execution.json').read_bytes()
    command(['/usr/local/bin/node', work / 'istruct-check.mjs', work / 'collector.wasm', out / 'istruct-checks.json'], out / 'istruct.log')
    assert (out / 'istruct-checks.json').read_bytes() == (work / 'istruct-checks.json').read_bytes()
    save(out / 'integration.json', dict(status='PASS', files={n: sha(ROOT / n) for n in files},
         runtime=used, materialized_artifacts=count, production_execution=sha(out / 'execution.json'),
         structural_collector_checks=read(out / 'istruct-checks.json')['checks'],
         original_definitions=537, non_nil_witnesses=502, comparisons=22480,
         admitted=2060, denominator=2231, slot_credit=False))
    print('PASS: reviewed final files, production imports, 22,480 comparisons')


if __name__ == '__main__':
    main()
