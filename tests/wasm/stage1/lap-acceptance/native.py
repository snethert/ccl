"""Qualify the accepted LAP compiler and source in pristine U1."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REVIEWED = '27f5bc02'
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'


def proposal(source, target):
    target.mkdir(parents=True)
    rows = subprocess.check_output([
        'git', '-C', str(ROOT), 'diff', '--name-status', U1, REVIEWED, '--',
        'compiler', 'level-0', 'level-1', 'lib', 'library', 'xdump'], text=True)
    manifest = dict(source_revision=U1, added=[], modified=[])
    for row in rows.splitlines():
        kind, name = row.split('\t')
        assert kind in ('A', 'M'), row
        reviewed = subprocess.check_output(['git', '-C', str(ROOT), 'show', REVIEWED + ':' + name])
        data = (ROOT / name).read_bytes()
        assert data == reviewed, name
        path = target / 'files' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        if kind == 'A':
            manifest['added'].append(dict(path=name, sha256=digest))
        else:
            manifest['modified'].append(dict(path=name,
                before=hashlib.sha256((source / name).read_bytes()).hexdigest(), after=digest))
    (target / 'unit.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    sys.setrecursionlimit(10000)
    fixture = HERE.parent / 'bootstrap-generic-dispatch'
    sys.path.insert(0, str(fixture))
    spec = importlib.util.spec_from_file_location('lap_native', fixture / 'native.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    native.driver.proposal = proposal
    evidence = ROOT.parent / 'ccl-evidence'
    raise SystemExit(native.driver.run(evidence / 'macos-u1-inputs',
        evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
        output / 'work', output / 'native', evidence / '2026-09-16-stage1-1a-r2/native'))
