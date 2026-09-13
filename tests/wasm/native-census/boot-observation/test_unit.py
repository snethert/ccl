#!/usr/bin/env python3
"""Exercise recovery and scope guards on tiny owned archives, never a checkout."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from unit import BootUnit
from build_patch import FILES, ROOT, U1, HERE


def test():
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='ccl-boot-unit-') as temp:
        root = Path(temp).resolve(); work = root / 'work'; source = work / 'ccl'; source.mkdir(parents=True)
        fixture = root / 'fixture'; fixture.mkdir()
        for name in ('patch.json', 'observation.patch'): shutil.copyfile(HERE / name, fixture / name)
        originals = {name: subprocess.check_output(['git', '-C', str(ROOT), 'show', U1 + ':' + name]) for name in FILES}
        for name, data in originals.items():
            p = source / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        marker = work / 'disposable.json'
        marker.write_text(json.dumps({'purpose': 'boot-census-disposable-U1', 'source': str(source)}))
        unit = BootUnit(work, fixture)
        with unit: unit.check('observed_sha256')
        unit.check('original_sha256'); outcomes.append({'name': 'apply-and-restore-all-three', 'status': 'PASS'})
        def reject(name, action):
            try: action()
            except ValueError as exc: outcomes.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
            else: raise ValueError('guard escaped: ' + name)
        (source / '.git').mkdir(); reject('checkout-refused', lambda: BootUnit(work, fixture)); (source / '.git').rmdir()
        manifest = json.loads((fixture / 'patch.json').read_text())
        damaged = dict(manifest, files=manifest['files'][:-1])
        (fixture / 'patch.json').write_text(json.dumps(damaged))
        reject('partial-unit-refused', lambda: BootUnit(work, fixture))
        (fixture / 'patch.json').write_text(json.dumps(manifest))
        patch = (fixture / 'observation.patch').read_bytes()
        (fixture / 'observation.patch').write_bytes(patch + b'\n')
        reject('changed-patch-refused', lambda: BootUnit(work, fixture))
        (fixture / 'observation.patch').write_bytes(patch)
        unit.apply(); name = FILES[0]; p = source / name
        p.write_bytes(originals[name]); unit.restore(); unit.check('original_sha256')
        outcomes.append({'name': 'interrupted-mixed-state-restored', 'status': 'PASS'})
        unit.apply(); observed = p.read_bytes(); p.write_bytes(observed + b'\n; unrelated edit\n')
        reject('unexplained-edit-preserved', unit.restore)
        if not p.read_bytes().endswith(b'; unrelated edit\n'): raise ValueError('guard overwrote an unrelated edit')
        p.write_bytes(observed); unit.restore()
        unit.apply(); backup = work / 'original-source' / name; saved = backup.read_bytes()
        backup.write_bytes(saved + b'\n')
        reject('damaged-backup-refused', unit.restore)
        backup.write_bytes(saved); unit.restore()
        if any('/X86/' in name or '/PPC/' in name or '/ARM/' in name for name in FILES):
            raise ValueError('native target source included in observation unit')
    return {'status': 'PASS', 'positive_cases': 2, 'controls_rejected': 5, 'outcomes': outcomes}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('output', type=Path); args = p.parse_args()
    result = test(); args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'positive_cases', 'controls_rejected')}))
