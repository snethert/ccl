"""Bind O-97/O-98 repair evidence without accepting or integrating it."""
from pathlib import Path
import argparse
import hashlib
import product
import storage

c = product.c


def retain(destination, execution, baseline, native, corpus, readers, collector, development, replay):
    roots = dict(execution=execution, baseline=baseline, native=native, corpus=corpus,
                 readers=readers, collector=collector, development=development)
    for path in roots.values(): storage.workspace(path)
    sources = {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    result = c.read(execution / 'summary.json')
    assert result['source_identity'] == sources and result['whole_file'] == [21, 21, 0]
    assert c.read(native / 'qualification.json')['source_identity'] == sources
    assert c.read(native / 'results/run.json')['status'] == 'PASS'
    regression = c.read(corpus / 'regression.json')
    assert regression['status'] == 'PASS' and regression['runtime'] == result['runtime']
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == sources
    reader = c.read(readers / 'summary.json')
    assert reader['status'] == 'PASS' and all(sources[n] == h['after'] for n, h in reader['full_sources'].items())
    checks = c.read(collector / 'summary.json')
    assert checks['status'] == 'PASS' and checks['runtime'] == result['runtime']
    assert len(checks['mutants']) == 10 and all(r['status'] == 'KILLED' for r in checks['mutants'])
    comparison = c.read(replay)
    assert comparison['status'] == 'PASS' and comparison['source_identity'] == sources
    for row in c.read(baseline / 'summary.json')['runs'].values():
        failure = next(r for r in row['failures'] if r['id'] == 'gc-fresh')
        assert failure['native_expected'] == [None, None] and failure['error'] == 'checked 10'
    inventory = c.read(execution / 'execution-files.json')
    c.verify_files(execution, inventory)
    assert {str(p.relative_to(execution)) for p in c.files(execution)} == set(inventory) | {'execution-files.json'}
    assert not (execution / 'diagnostic.mjs').exists()
    record = dict(status='PROPOSED', review='NOT_REVIEWED', whole_file=result['whole_file'],
        execution_status=result['status'], source_identity=sources, runtime=result['runtime'],
        all_proposal_sources={n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.all_sources().items()},
        accepted_originals=[575, 535], ledger=[21, 12], target_load=False, boot=False,
        parent=c.read(product.HERE / 'files/parent.json'), audit='f716268ee8752c26fe89ba4d5449daf58e9b9262',
        native_inputs=c.sha(c.STORE / 'macos-u1-inputs/pins.json'))
    product.module('retain_reports', product.HERE.parent / 'loader-chain/retain.py').retain(
        c, destination, roots, 'STAGE1-LOADER-GC-R1', record, {'replay.json': comparison})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'baseline', 'native', 'corpus', 'readers', 'collector', 'development', 'replay'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = vars(parser.parse_args())
    with storage.lease([p for n, p in args.items() if n not in ('destination', 'replay')]): retain(**args)
