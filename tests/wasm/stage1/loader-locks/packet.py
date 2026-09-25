"""Retain one bounded loader-lock packet; never rewrite predecessor evidence."""
from pathlib import Path
import argparse
import gzip
import hashlib
import os
import shutil
import tempfile
import product

HERE = Path(__file__).resolve().parent
c = product.c


def retain(destination, execution, native, corpus, readers, replay, development):
    assert not destination.exists()
    identity = {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    result = c.read(execution / 'summary.json')
    for path in (execution / 'summary.json', native / 'qualification.json', replay / 'summary.json'):
        value = c.read(path)
        assert value['status'] == 'PASS' and value['source_identity'] == identity, path
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == identity
    assert c.read(corpus / 'regression.json')['fresh_comparisons'] == 26048
    assert c.read(native / 'results/run.json')['status'] == 'PASS'
    assert c.read(execution / 'initializer-control.json')['status'] == 'KILLED'
    reader = c.read(readers / 'positive/summary.json')
    assert reader['status'] == 'PASS' and reader['comparisons'] == 34
    assert c.read(readers / 'mutant.json')['status'] == 'KILLED'
    for name, row in reader['full_sources'].items():
        assert row['after'] == identity[name]
    stage = Path(tempfile.mkdtemp(prefix='.loader-locks-retaining-', dir=destination.parent))
    compressed, regenerable = {}, {}

    def copy(path, name):
        name = Path(name)
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = c.sha(path)
        entry = dict(sha256=digest, bytes=path.stat().st_size)
        if (path.suffix in ('.image', '.dx64fsl', '.w32fsl', '.wasm', '.wat', '.bin')
                or path.name == 'dx86cl64' or path.name.endswith(('.instructions.txt', '.sections.txt'))):
            regenerable[str(name)] = entry
        elif path.stat().st_size > 131072:
            target = target.with_name(target.name + '.gz')
            with path.open('rb') as source, target.open('wb') as output:
                with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as stream:
                    shutil.copyfileobj(source, stream)
            with gzip.open(target, 'rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest
            compressed[str(name)] = dict(file=str(target.relative_to(stage)), **entry)
        else:
            shutil.copyfile(path, target)
            assert c.sha(target) == digest

    def tree(root, label):
        for path in c.files(root):
            if not path.name.startswith('.'):
                copy(path, Path(label) / path.relative_to(root))

    try:
        tree(HERE, 'source')
        tree(execution, 'execution')
        for root, label in ((native, 'native'), (native / 'results', 'native/results'),
                            (corpus, 'corpus'), (corpus / 'base', 'corpus/base')):
            for path in root.iterdir():
                if path.is_file() and path.suffix in ('.json', '.log', '.lisp'):
                    copy(path, Path(label) / path.name)
        # Native test suite reports are small, separate from the build tree.
        for name in ('baseline-tests', 'registered-tests'):
            if (native / 'results' / name).is_dir():
                tree(native / 'results' / name, 'native/results/' + name)
        tree(readers, 'readers')
        for name in ('summary.json', 'run.log', 'exercise.log'):
            copy(replay / name, Path('replay') / name)
        # Keep failure logs, exact assembled witnesses and source identities;
        # exclude duplicate heaps/modules/runtime trees and intermediate builds.
        for path in c.files(development):
            relative = path.relative_to(development)
            if (len(relative.parts) <= 2 and path.suffix in ('.json', '.log', '.lisp', '.py')
                    and not path.name.startswith('.')):
                copy(path, Path('development') / relative)
        dependencies = {}
        for folder in ('loader', 'loader-level0', 'bootstrap-validation'):
            for path in c.files(HERE.parent / folder):
                if path.suffix in ('.py', '.lisp', '.json', '.mjs'):
                    dependencies[str(path.relative_to(c.ROOT))] = c.sha(path)
        c.save(stage / 'dependencies.json', dependencies)
        c.save(stage / 'summary.json', dict(status='PASS', review='NOT_REVIEWED',
            integration=False, source_identity=identity, executions=result,
            native_tests=21843, native_fasls_restored=164, native_identical=45,
            native_decoded_equal=119, reader_comparisons=34, reader_profiles=17,
            compiler_comparisons=26048, replay=c.read(replay / 'summary.json'),
            native_promotion_boundary=c.read(development / 'native-promotion-timeout/result.json'),
            accepted_files=[0, 0, 0], accepted_originals=[575, 535], ledger=[21, 12],
            slot_credit=False, target_load=False, boot=False,
            references={name: c.sha(c.STORE / name) for name in (
                '2026-09-25-loader-set-package-r1/packet.json',
                '2026-09-25-loader-integration/packet.json', 'macos-u1-inputs/pins.json')}))
        c.save(stage / 'compressed.json', compressed)
        c.save(stage / 'regenerable.json', regenerable)
        c.save(stage / 'packet.json', dict(id='STAGE1-LOADER-LOCKS-R1',
            status='PROPOSED', review='NOT_REVIEWED', slot_credit=False, files=c.inventory(stage)))
        c.verify_files(stage, c.read(stage / 'packet.json')['files'])
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return dict(status='PASS', path=str(destination), sha256=c.sha(destination / 'packet.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'native', 'corpus', 'readers', 'replay', 'development'):
        parser.add_argument('--' + name, type=Path, required=True)
    print(retain(**vars(parser.parse_args())))
