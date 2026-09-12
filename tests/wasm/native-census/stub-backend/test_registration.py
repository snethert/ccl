#!/usr/bin/env python3
"""Exercise reversible-unit failure paths in tiny owned fixtures, without native rebuilds."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from registration import Registration
from reversible import digest, save

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def run():
    controls = []; positives = []
    with tempfile.TemporaryDirectory(prefix='ccl-stub-unit-') as temp:
        work = Path(temp).resolve(); source = work / 'ccl'; (source / 'lib').mkdir(parents=True)
        original = (ROOT / 'lib/systems.lisp').read_bytes()
        target = source / 'lib/systems.lisp'; target.write_bytes(original)
        save(work / 'disposable.json', {'purpose': 'census-stub-disposable-U1', 'source': str(source)})
        unit = Registration(work, HERE)
        def rejected(name, action):
            try: action()
            except ValueError as exc: controls.append({'control': name, 'status': 'REJECTED', 'reason': str(exc)})
            else: raise ValueError('unit control escaped: ' + name)
        with unit:
            assert digest(target) == unit.manifest['modified'][0]['after_sha256']
            for r in unit.manifest['added']: assert digest(source / r['path']) == r['sha256']
            rejected('double-application', unit.apply)
        assert target.read_bytes() == original and not (source / 'compiler/WASM-CENSUS').exists()
        positives.append('complete apply/remove')
        target.write_bytes(original + b'\n; unexplained\n')
        rejected('changed-upstream-source', unit.apply)
        assert target.read_bytes().endswith(b'; unexplained\n'); target.write_bytes(original)
        occupied = source / unit.manifest['added'][0]['path']; occupied.parent.mkdir(parents=True)
        occupied.write_text('existing data')
        rejected('occupied-addition', unit.apply)
        assert occupied.read_text() == 'existing data'; occupied.unlink(); occupied.parent.rmdir()
        unit.apply(); patched = target.read_bytes(); target.write_bytes(patched + b'\n; external edit\n')
        rejected('unexplained-edit-on-removal', unit.restore)
        assert target.read_bytes().endswith(b'; external edit\n'); target.write_bytes(patched); unit.restore()
        unit.apply(); backup = work / 'original-systems.lisp'; backup.write_text('damaged')
        rejected('damaged-recovery-backup', unit.restore)
        assert target.read_bytes() == patched; backup.write_bytes(original); unit.restore()
        unit.apply(); (source / unit.manifest['added'][0]['path']).unlink()
        unit.restore()
        assert target.read_bytes() == original and not (source / 'compiler/WASM-CENSUS').exists()
        positives.append('partial addition removal')
        marker = work / 'disposable.json'; good = marker.read_bytes(); marker.write_text('{}')
        rejected('missing-ownership', lambda: Registration(work, HERE)); marker.write_bytes(good)
    return {'status': 'PASS', 'positive_cases': positives, 'controls': controls}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): p.error('never overwrite a retained result')
    report = run(); save(a.output, report)
    print(json.dumps({'status': report['status'], 'positive_cases': len(report['positive_cases']), 'controls_rejected': len(report['controls'])}))
