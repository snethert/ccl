"""Retain one proposal, qualification, and original failure logs; prune outputs."""
from pathlib import Path
import argparse
import gzip
import hashlib
import os
import shutil
import tempfile
import product
import storage

c = product.c


def retain(destination, execution, native, corpus, readers, collector, development):
    assert not destination.exists()
    roots = dict(execution=execution, native=native, corpus=corpus,
                 readers=readers, collector=collector, development=development)
    for p in roots.values(): storage.workspace(p)
    sources = {n: hashlib.sha256(b.encode()).hexdigest() for n,b in product.sources().items()}
    result = c.read(execution / 'summary.json')
    assert result['source_identity'] == sources
    assert result['whole_file'] == [20, 20, 0]
    assert c.read(native / 'qualification.json')['source_identity'] == sources
    assert c.read(native / 'results/run.json')['status'] == 'PASS'
    regression = c.read(corpus / 'regression.json')
    assert regression['status'] == 'PASS' and regression['runtime'] == result['runtime']
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == sources
    reader = c.read(readers / 'summary.json')
    assert reader['status'] == 'PASS' and all(sources[n] == h['after'] for n,h in reader['full_sources'].items())
    assert c.read(collector / 'summary.json')['runtime'] == result['runtime']
    stage = Path(tempfile.mkdtemp(prefix='.loader-hash-', dir=destination.parent))
    generated, compressed = {}, {}
    try:
        for label, root in dict(roots, source=product.HERE, drivers=product.HERE.parent / 'loader-chain').items():
            for path in c.files(root):
                rel = path.relative_to(root)
                if rel.parts[0] in ('work', 'native-source') or any(x.startswith('u1-') for x in rel.parts):
                    continue
                # Corpus sessions are cached; preserve their reports and identities.
                if label == 'corpus' and len(rel.parts)>2: continue
                if label == 'development' and path.suffix not in ('.log', '.json', '.patch', '.py', '.lisp', '.mjs'): continue
                name = str(Path(label) / rel)
                row = dict(sha256=c.sha(path), bytes=path.stat().st_size)
                if path.suffix in ('.wasm', '.wat', '.bin', '.w32fsl', '.dx64fsl', '.image') or path.name == 'dx86cl64':
                    generated[name] = row
                    continue
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
        c.save(stage / 'summary.json', dict(status='PROPOSED', review='NOT_REVIEWED',
            whole_file=result['whole_file'], execution_status=result['status'],
            source_identity=sources, runtime=result['runtime'],
            accepted_originals=[575, 535], ledger=[21, 12], target_load=False, boot=False,
            git_free_replay='not run; reproducible commands retained',
            parent=c.read(product.HERE / 'files/parent.json')['revision'],
            native_inputs=c.sha(c.STORE / 'macos-u1-inputs/pins.json')))
        c.save(stage / 'regenerable.json', generated)
        c.save(stage / 'compressed.json', compressed)
        c.save(stage / 'packet.json', dict(id='STAGE1-LOADER-HASH-IO-R1', status='PROPOSED', files=c.inventory(stage)))
        c.verify_files(stage, c.read(stage / 'packet.json')['files'])
        os.rename(stage, destination)
    finally:
        if stage.exists(): shutil.rmtree(stage)
    print(dict(path=str(destination), sha256=c.sha(destination / 'packet.json')))
    for p in roots.values(): shutil.rmtree(p)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'native', 'corpus', 'readers', 'collector', 'development'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = vars(parser.parse_args())
    with storage.lease([p for n,p in args.items() if n != 'destination']): retain(**args)
