"""Retain one qualified loader proposal and the original development failures."""
from pathlib import Path
import argparse
import gzip
import hashlib
import os
import shutil
import tempfile
import product
import identity

c = product.c


def retain(destination, execution, native, corpus, readers, replay, development):
    assert not destination.exists()
    sources = {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    result = c.read(execution / 'summary.json')
    assert result['status'] == 'PASS' and result['source_identity'] == sources
    assert c.read(native / 'qualification.json')['source_identity'] == sources
    assert c.read(native / 'results/run.json')['status'] == 'PASS'
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == sources
    regression = c.read(corpus / 'regression.json')
    assert regression['status'] == 'PASS' and regression['fresh_comparisons'] == 26048
    assert regression['runtime'] == result['runtime']
    assert c.read(readers / 'summary.json')['status'] == 'PASS'
    assert c.read(replay / 'summary.json')['source_identity'] == sources
    assert c.read(execution / 'proposal-inputs.json') == identity.drivers()
    assert c.read(replay / 'summary.json')['drivers'] == identity.drivers()
    parent = c.STORE / '2026-09-25-loader-general-aref-r1'
    collector = c.read(parent / 'collector/summary.json')
    assert collector['status'] == 'PASS' and collector['source'] == result['runtime']['source']
    stage = Path(tempfile.mkdtemp(prefix='.loader-new-ptr-', dir=destination.parent))
    compressed, generated = {}, {}

    def copy(path, name):
        name = Path(name)
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = c.sha(path)
        row = dict(sha256=digest, bytes=path.stat().st_size)
        if (path.suffix in ('.image', '.dx64fsl', '.w32fsl', '.wasm', '.wat', '.bin')
                or path.name == 'dx86cl64' or path.name.endswith(('.instructions.txt', '.sections.txt'))):
            generated[str(name)] = row
        elif path.stat().st_size > 131072:
            target = target.with_name(target.name + '.gz')
            with path.open('rb') as source, target.open('wb') as output:
                with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as stream:
                    shutil.copyfileobj(source, stream)
            with gzip.open(target, 'rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest
            compressed[str(name)] = dict(file=str(target.relative_to(stage)), **row)
        else:
            shutil.copyfile(path, target)
            assert c.sha(target) == digest

    try:
        for folder, label in ((product.HERE, 'source'), (execution, 'execution'),
                              (readers, 'readers'), (development, 'development')):
            for path in c.files(folder):
                relative = path.relative_to(folder)
                if not path.name.startswith('.') and 'runtime' not in relative.parts:
                    copy(path, Path(label) / relative)
        for folder, label in ((native, 'native'), (native / 'results', 'native/results'),
                              (corpus, 'corpus'), (corpus / 'base', 'corpus/base')):
            for path in folder.iterdir():
                if path.is_file() and path.suffix in ('.json', '.log', '.lisp'):
                    copy(path, Path(label) / path.name)
        for name in ('summary.json', 'run.log', 'exercise.log'):
            copy(replay / name, Path('replay') / name)
        for name in ('baseline-tests', 'registered-tests'):
            for path in c.files(native / 'results' / name):
                copy(path, Path('native/results') / name / path.relative_to(native / 'results' / name))
        c.save(stage / 'summary.json', dict(status='PASS', review='NOT_REVIEWED',
            product_integration=False, source_identity=sources, execution=result,
            native_tests=21843, restored_fasls=164, compiler_comparisons=26048,
            readers=c.read(readers / 'summary.json'), collector_reused=c.sha(parent / 'collector/summary.json'),
            replay=dict(status='PASS', artifacts=len(c.read(replay / 'summary.json')['artifacts'])),
            accepted_files=[0, 0, 0], accepted_originals=[575, 535], ledger=[21, 12],
            slot_credit=False, target_load=False, boot=False,
            references={name: c.sha(c.STORE / name) for name in (
                '2026-09-25-loader-general-aref-r1/packet.json',
                '2026-09-25-loader-prefix-integration/packet.json', 'macos-u1-inputs/pins.json')}))
        c.save(stage / 'compressed.json', compressed)
        c.save(stage / 'regenerable.json', generated)
        c.save(stage / 'packet.json', dict(id='STAGE1-LOADER-NEW-PTR-R1',
            status='PROPOSED', review='NOT_REVIEWED', slot_credit=False, files=c.inventory(stage)))
        c.verify_files(stage, c.read(stage / 'packet.json')['files'])
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(dict(status='PASS', path=str(destination), sha256=c.sha(destination / 'packet.json')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'native', 'corpus', 'readers', 'replay', 'development'):
        parser.add_argument('--' + name, type=Path, required=True)
    retain(**vars(parser.parse_args()))
