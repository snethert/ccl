#!/usr/bin/env python3
"""Exercise recovery of FASLs and both image names, including damaged backups."""
import json
from pathlib import Path
import tempfile
from run import restore_clean_outputs
from reversible import digest, save


def exercise():
    with tempfile.TemporaryDirectory(prefix='ccl-output-reversal-') as name:
        work = Path(name); source = work / 'ccl'; backup = work / 'clean'
        rows = []
        for n in ['bin/nfcomp.dx64fsl', 'l1-fasls/nx.dx64fsl', 'dx86cl64',
                  'dx86cl64.image', 'x86-boot64.image']:
            p = backup / n; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(('clean:' + n).encode())
            q = source / n; q.parent.mkdir(parents=True, exist_ok=True)
            q.write_bytes(('observed:' + n).encode())
            rows.append({'path': n, 'backup': str(p), 'sha256': digest(p)})
        save(work / 'clean-baseline.json', {'files': rows})
        extra = source / 'extra.dx64fsl'; extra.write_bytes(b'observed extra')
        restore_clean_outputs(work)
        assert all(digest(source / r['path']) == r['sha256'] for r in rows)
        assert not extra.exists()
        restore_clean_outputs(work)
        assert all(digest(source / r['path']) == r['sha256'] for r in rows)
        Path(rows[-1]['backup']).write_bytes(b'damaged boot image backup')
        before = {r['path']: (source / r['path']).read_bytes() for r in rows}
        try: restore_clean_outputs(work)
        except ValueError: pass
        else: raise AssertionError('damaged backup accepted')
        assert all((source / n).read_bytes() == b for n, b in before.items())
    print(json.dumps({'status': 'PASS', 'controls': [
        'FASLs, kernel, normal image and boot image restored; extra FASL removed',
        'repeated recovery preserves clean bytes', 'damaged backup rejected before mutation']}))


if __name__ == '__main__': exercise()
