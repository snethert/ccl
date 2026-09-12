#!/usr/bin/env python3
"""Exercise the real patch, cleanup and interrupted-unit recovery on U1 copies."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from reversible import ObservationUnit, digest, save

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
manifest = json.loads((HERE / 'patch.json').read_text())
passed = []


def fresh(root):
    work = root / str(len(passed)); work.mkdir()
    source = work / 'ccl'; source.mkdir()
    for r in manifest['files']:
        p = source / r['path']; p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / r['path'], p)
    save(work / 'disposable.json', {'purpose': 'native-census-disposable-U1', 'source': str(source)})
    return ObservationUnit(work, HERE)


with tempfile.TemporaryDirectory(prefix='ccl-census-reversal-controls-') as temp:
    root = Path(temp).resolve()
    unit = fresh(root)
    with unit: unit.check('observed_sha256')
    unit.check('original_sha256'); passed.append('complete patch applies and reverses exactly')

    unit = fresh(root)
    try:
        with unit: raise RuntimeError('injected native execution failure')
    except RuntimeError: pass
    unit.check('original_sha256'); passed.append('execution failure reverses the whole unit')

    unit = fresh(root)
    try:
        with unit: raise KeyboardInterrupt()
    except KeyboardInterrupt: pass
    unit.check('original_sha256'); passed.append('interrupt reverses the whole unit')

    unit = fresh(root); unit.apply()
    r = manifest['files'][0]
    shutil.copyfile(unit.work / 'original-source' / r['path'], unit.source / r['path'])
    subprocess.run([sys.executable, '-c',
                    'import sys; from reversible import ObservationUnit; '
                    'u = ObservationUnit(sys.argv[1], sys.argv[2]); '
                    'u.restore(); u.check("original_sha256")',
                    str(unit.work), str(HERE)], cwd=HERE, check=True)
    unit.check('original_sha256')
    passed.append('new process recovers a partially removed unit')

    unit = fresh(root); unit.apply(); unit.restore(); unit.restore(); unit.check('original_sha256')
    passed.append('completed recovery is idempotent')

    unit = fresh(root); p = unit.source / manifest['files'][0]['path']; p.write_text(p.read_text() + '\n; unknown edit\n')
    before = [digest(unit.source / r['path']) for r in manifest['files']]
    try: unit.apply(); raise AssertionError('unexpected source accepted')
    except ValueError: pass
    assert before == [digest(unit.source / r['path']) for r in manifest['files']]
    passed.append('wrong baseline rejected before any source mutation')

    unit = fresh(root); unit.apply(); p = unit.source / manifest['files'][0]['path']
    p.write_text(p.read_text() + '\n; unrelated concurrent change\n'); original = p.read_bytes()
    try: unit.restore(); raise AssertionError('unknown edit overwritten')
    except ValueError: pass
    assert p.read_bytes() == original
    passed.append('unexplained external changes preserved and recovery refused')

    unit = fresh(root); (unit.source / '.git').mkdir()
    try: ObservationUnit(unit.work, HERE); raise AssertionError('working checkout accepted')
    except ValueError: pass
    passed.append('Git checkout refused even with a disposable marker')

print(json.dumps({'status': 'PASS', 'controls': passed}, indent=2))
