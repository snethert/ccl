"""Retain fresh integration reports; leave every predecessor packet immutable."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile
import check

spec = importlib.util.spec_from_file_location('prefix_integration_run', check.HERE / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)

c = check.c


def retain(out, destination):
    assert not destination.exists()
    result = c.read(out / 'integration.json')
    assert result['status'] == 'PASS' and result['new_execution']
    assert result['drivers'] == run.drivers()
    assert result['integration_record'] == c.sha(check.RECORD)
    assert result['source_identity'] == check.check()['source_identity']
    stage = Path(tempfile.mkdtemp(prefix='.prefix-integration-', dir=destination.parent))
    generated, compressed = {}, {}

    def copy(path, name):
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        row = dict(sha256=c.sha(path), bytes=path.stat().st_size)
        if path.suffix in ('.image', '.dx64fsl', '.w32fsl', '.wasm', '.wat', '.bin') or path.name == 'dx86cl64':
            generated[str(name)] = row
        elif path.stat().st_size > 131072:
            target = target.with_name(target.name + '.gz')
            with path.open('rb') as source, target.open('wb') as output:
                with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as stream:
                    shutil.copyfileobj(source, stream)
            with gzip.open(target, 'rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
            compressed[str(name)] = dict(file=str(target.relative_to(stage)), **row)
        else:
            shutil.copyfile(path, target)
            assert c.sha(target) == row['sha256']

    try:
        for path in c.files(out):
            relative = path.relative_to(out)
            if not path.name.startswith('.') and 'runtime' not in relative.parts:
                copy(path, relative)
        for path in c.files(check.HERE):
            copy(path, Path('source') / path.name)
        copy(check.RECORD, Path('source/integration-loader-prefix.json'))
        c.save(stage / 'regenerable.json', generated)
        c.save(stage / 'compressed.json', compressed)
        c.save(stage / 'packet.json', dict(id='STAGE1-LOADER-PREFIX-INTEGRATION',
            status='ACCEPTED_AND_INTEGRATED', review='AUDIT_180_NO_DEFECT',
            slot_credit=False, files=c.inventory(stage)))
        c.verify_files(stage, c.read(stage / 'packet.json')['files'])
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(dict(status='PASS', packet=str(destination), sha256=c.sha(destination / 'packet.json')))


if __name__ == '__main__':
    retain(*(Path(p).resolve() for p in sys.argv[1:]))
