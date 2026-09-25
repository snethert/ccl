"""Retain one bounded SET-PACKAGE review packet, including original failures."""
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


def retain(destination, execution, native, corpus, replay, readers, controls, regression, development):
    assert not destination.exists()
    identity = {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    result = c.read(execution / 'summary.json')
    assert identity == result['source_identity']
    assert identity == c.read(native / 'qualification.json')['source_identity']
    assert identity == c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources']
    assert identity == c.read(replay / 'summary.json')['source_identity']
    assert identity == c.read(regression / 'execution/summary.json')['proposal_source_identity']
    for path in (execution / 'summary.json', native / 'results/run.json', corpus / 'regression.json',
                 replay / 'summary.json', readers / 'positive/summary.json', controls / 'summary.json',
                 regression / 'summary.json'):
        assert c.read(path)['status'] == 'PASS', path
    assert c.read(readers / 'mutant.json')['status'] == 'KILLED'
    assert c.read(readers / 'positive/summary.json')['full_sources']['level-0/nfasload.lisp']['after'] == identity['level-0/nfasload.lisp']
    assert c.read(corpus / 'regression.json')['fresh_comparisons'] == 26048
    temporary = Path(tempfile.mkdtemp(prefix='.loader-level0-retaining-', dir=destination.parent))
    regenerable, compressed = {}, {}

    def copy(path, name):
        target = temporary / name
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
            compressed[str(name)] = dict(file=str(target.relative_to(temporary)), **entry)
        else:
            shutil.copyfile(path, target)
            assert c.sha(target) == digest

    def tree(folder, label):
        for path in c.files(folder):
            if '__pycache__' not in path.parts and not path.name.startswith('.'):
                copy(path, Path(label) / path.relative_to(folder))

    try:
        tree(HERE, 'source')
        copy(HERE.parent / 'loader/d2.mjs', Path('source/loader-d2.mjs'))
        tree(execution, 'execution')
        for path in native.iterdir():
            if path.is_file():
                copy(path, Path('native') / path.name)
        for path in (native / 'results').iterdir():
            if path.is_file() and not path.name.startswith('baseline'):
                copy(path, Path('native/results') / path.name)
        for path in corpus.iterdir():
            if path.is_file():
                copy(path, Path('corpus') / path.name)
        for path in (corpus / 'base').iterdir():
            if path.is_file() and path.suffix in ('.json', '.log'):
                copy(path, Path('corpus/base') / path.name)
        for name in ('native.json', 'modules.json'):
            copy(corpus / 'base/compiled' / name, Path('corpus') / name)
        for label, folder in [('readers', readers), ('controls', controls)]:
            tree(folder, label)
        for name in ('summary.json', 'replay.log'):
            copy(replay / name, Path('replay') / name)
        for name in ('summary.json', 'execution/summary.json', 'extra/summary.json',
                     'extra/keyword-mutant.log', 'extra/compatibility.log'):
            copy(regression / name, Path('regression') / name)
        # Development keeps diagnostics and input identities, never repeated
        # image trees, module listings or baseline builds. Debug instrumentation
        # is segregated here and is absent from the verified execution.
        for path in c.files(development):
            name = path.relative_to(development)
            if name.parts[0] == execution.name or any(x in name.parts for x in
                    ('artifacts', 'artifacts-complete', 'runtime', 'prefix', 'keywords', '__pycache__')):
                continue
            if len(name.parts) <= 3 and path.suffix in ('.json', '.log', '.patch', '.md', '.py', '.mjs', '.lisp'):
                copy(path, Path('development') / name)
        c.save(temporary / 'summary.json', dict(
            status='PASS', review='NOT_REVIEWED', product_integration=False,
            source_identity=identity, native_tests=21843, compiler_comparisons=26048,
            reader_profiles=17, results=result['results'], ordered=result['ordered'],
            controls=c.read(controls / 'summary.json'),
            fasl_metadata_controls=5, p2_0_regression=c.read(regression / 'summary.json'),
            replay='byte-identical producer/artifacts and equal observations; Git-free different root',
            production_files=[0, 0, 0], accepted_originals=[575, 535], ledger=[21, 12],
            slot_credit=False, boot=False, target_load=False,
            base_commit='3687d511', accepted_loader='50cd8ea1',
            references={n: c.sha(c.STORE / n) for n in (
                '2026-09-25-loader-integration/packet.json',
                '2026-09-25-loader-design-r1/packet.json',
                'macos-u1-inputs/pins.json')}))
        c.save(temporary / 'regenerable.json', regenerable)
        c.save(temporary / 'compressed.json', compressed)
        c.save(temporary / 'packet.json', dict(id='STAGE1-LOADER-SET-PACKAGE-R1',
            status='PROPOSED', review='NOT_REVIEWED', slot_credit=False, files=c.inventory(temporary)))
        c.verify_files(temporary, c.read(temporary / 'packet.json')['files'])
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return dict(status='PASS', packet=str(destination), sha256=c.sha(destination / 'packet.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'native', 'corpus', 'replay', 'readers',
                 'controls', 'regression', 'development'):
        parser.add_argument('--' + name, type=Path, required=True)
    print(retain(**vars(parser.parse_args())))
