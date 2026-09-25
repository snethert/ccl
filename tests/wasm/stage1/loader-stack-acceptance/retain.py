"""Retain one integration packet, its killed mutant and its Git-free replay."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile
import check

spec = importlib.util.spec_from_file_location('stack_integration_run', check.HERE / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)

c = check.c


def retain(out, mutant, replay, development, destination):
    assert not destination.exists()
    result = c.read(out / 'integration.json')
    assert result['status'] == 'PASS' and result['new_execution']
    assert result['drivers'] == run.drivers()
    assert result['integration_record'] == c.sha(check.RECORD)
    assert result['source_identity'] == check.check()['source_identity']
    for path, is_mutant in ((out, False), (mutant, True)):
        finished = c.read(path / 'finished.json')
        assert finished['status'] == 'PASS' and finished['drivers'] == run.drivers()
        assert finished['mutant'] == is_mutant
    assert c.read(mutant / 'mutant.json')['status'] == 'PASS'
    assert c.read(replay / 'summary.json')['drivers'] == run.drivers()
    stage = Path(tempfile.mkdtemp(prefix='.stack-integration-', dir=destination.parent))
    generated, compressed = {}, {}

    def copy(path, name):
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        row = dict(sha256=c.sha(path), bytes=path.stat().st_size)
        if (path.suffix in ('.image', '.dx64fsl', '.w32fsl', '.wasm', '.wat', '.bin')
                or path.name == 'dx86cl64' or path.name.endswith(('.instructions.txt', '.sections.txt'))):
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
        for folder, label in ((out, 'positive'), (mutant, 'mutant'), (development, 'development')):
            for path in c.files(folder):
                relative = path.relative_to(folder)
                if not path.name.startswith('.') and 'runtime' not in relative.parts:
                    copy(path, Path(label) / relative)
        for name in ('summary.json', 'run.log'):
            copy(replay / name, Path('replay') / name)
        for path in c.files(check.HERE):
            copy(path, Path('source/loader-stack-acceptance') / path.name)
        for name in ('loader-def/exercise.py', 'loader-def/witnesses.lisp', 'loader-new-ptr/exercise.py'):
            copy(check.HERE.parent / name, Path('source') / name)
        copy(check.RECORD, Path('source/integration-loader-stack.json'))
        c.save(stage / 'summary.json', dict(status='PASS', product_integration=True,
            review='AUDIT_181_NO_DEFECT', follow_up_review='PENDING_HARNESS_REVIEW',
            integration=result, mutant=c.read(mutant / 'mutant.json'),
            replay_artifacts=len(c.read(replay / 'summary.json')['artifacts']),
            accepted_files=[0,0,0], accepted_originals=[575,535], ledger=[21,12],
            slot_credit=False, target_load=False, boot=False))
        c.save(stage / 'regenerable.json', generated)
        c.save(stage / 'compressed.json', compressed)
        c.save(stage / 'packet.json', dict(id='STAGE1-LOADER-STACK-INTEGRATION',
            status='ACCEPTED_AND_INTEGRATED', review='AUDIT_181_NO_DEFECT',
            follow_up_review='PENDING_HARNESS_REVIEW', slot_credit=False, files=c.inventory(stage)))
        c.verify_files(stage, c.read(stage / 'packet.json')['files'])
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(dict(status='PASS', packet=str(destination), sha256=c.sha(destination / 'packet.json')))
    for path in (out, mutant, replay, development):
        shutil.rmtree(path)


if __name__ == '__main__':
    paths = [Path(p).resolve() for p in sys.argv[1:]]
    with run.storage.lease(paths[:4]):
        retain(*paths)
