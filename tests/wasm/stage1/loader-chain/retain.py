"""Keep one verified report pack; inventory reproducible binaries by hash."""
from pathlib import Path
import gzip
import hashlib
import os
import shutil
import tempfile


def retain(c, destination, roots, identity, record, extra=None):
    assert not destination.exists()
    stage = Path(tempfile.mkdtemp(prefix='.loader-report-', dir=destination.parent))
    generated, compressed = {}, {}
    try:
        for label, root in roots.items():
            for path in c.files(root):
                rel = path.relative_to(root)
                if rel.parts[0] in ('work', 'native-source', 'files') or any(x.startswith('u1-') for x in rel.parts): continue
                if label == 'corpus' and len(rel.parts) > 2: continue
                if label == 'baseline' and (len(rel.parts) > 1 or path.suffix not in ('.json', '.log', '.lisp')): continue
                if label == 'development' and path.suffix not in ('.log', '.json', '.patch', '.lisp', '.mjs', '.txt', '.py'): continue
                name = str(Path(label) / rel)
                row = dict(sha256=c.sha(path), bytes=path.stat().st_size)
                if path.suffix in ('.wasm', '.wat', '.bin', '.w32fsl', '.dx64fsl', '.image') or path.name == 'dx86cl64':
                    generated[name] = row; continue
                target = stage / name; target.parent.mkdir(parents=True, exist_ok=True)
                if row['bytes'] > 131072:
                    target = target.with_name(target.name + '.gz')
                    with path.open('rb') as src, target.open('wb') as dst:
                        with gzip.GzipFile(filename='', mode='wb', fileobj=dst, mtime=0) as stream:
                            shutil.copyfileobj(src, stream)
                    with gzip.open(target, 'rb') as stream:
                        assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
                    compressed[name] = dict(file=str(target.relative_to(stage)), **row)
                else:
                    shutil.copyfile(path, target)
                    assert c.sha(target) == row['sha256']
        for name, value in (extra or {}).items(): c.save(stage / name, value)
        c.save(stage / 'summary.json', record)
        c.save(stage / 'regenerable.json', generated)
        c.save(stage / 'compressed.json', compressed)
        c.save(stage / 'packet.json', dict(id=identity, status='PROPOSED', files=c.inventory(stage)))
        c.verify_files(stage, c.read(stage / 'packet.json')['files'])
        os.rename(stage, destination)
    finally:
        if stage.exists(): shutil.rmtree(stage)
    print(dict(path=str(destination), sha256=c.sha(destination / 'packet.json')))
