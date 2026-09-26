"""Retain the verified direct-checkout deliverable, without acceptance credit."""
from pathlib import Path
import argparse
import hashlib
import shutil
import product
import storage

c, HERE = product.c, product.HERE


def retain(destination, execution, native, readers, corpus, development):
    sources = {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    result = c.read(execution / 'summary.json')
    assert result['source_identity'] == sources
    assert result['whole_file'] == [36, 36, 0]
    c.verify_files(execution, c.read(execution / 'artifacts.json'))
    assert c.read(native / 'qualification.json')['source_identity'] == sources
    assert c.read(native / 'results/run.json')['status'] == 'PASS'
    build_log = (native / 'results/registered-build.log').read_text()
    for name in ('FIND-XLOAD-BACKEND', 'BACKEND-XLOAD-INFO-COMPILE-FILE-FUNCTION'):
        assert 'Undefined function ' + name not in build_log
    matrix = c.read(readers / 'summary.json')
    assert matrix['status'] == 'PASS' and matrix['comparisons'] == 221
    assert all(sources[n] == r['after'] for n, r in matrix['full_sources'].items())
    regression = c.read(corpus / 'regression.json')
    assert regression['status'] == 'PASS' and regression['fresh_comparisons'] == 26112
    assert regression['runtime'] == result['runtime']
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == sources
    dispatch = c.read(execution / 'dispatch.json')
    assert dispatch['status'] == 'PASS' and len(dispatch['rows']) == 18
    assert all(r['dispatch'] and r['unchanged_input_skipped'] for r in dispatch['rows'])
    assert c.read(execution / 'cold-eval-controls.json')['status'] == 'PASS'
    prior = c.STORE / '2026-09-26-weak-hash-r1'
    assert c.sha(prior / 'packet.json') == 'db324e5c84377e85e567aea95bf622620799cb20717e9c887360c8c824d9b082'
    files = {row['path']: row['sha256'] for row in c.read(prior / 'packet.json')['files']}
    assert c.sha(prior / 'collector/summary.json') == files['collector/summary.json']
    collector = c.read(prior / 'collector/summary.json')
    assert collector['status'] == 'PASS' and collector['checks']['checks'] == 123
    assert len(collector['mutants']) == 17
    assert all(row['status'] == 'KILLED' for row in collector['mutants'])
    assert result['runtime'] == collector['runtime']
    assert c.sha(c.ROOT / 'runtime/wasm32/collector.c') == collector['runtime']['source']
    assert c.sha(c.ROOT / 'runtime/wasm32/collector-owner.mjs') == collector['runtime']['owner']
    record = dict(status='IMPLEMENTED_AWAITING_REVIEW', review='NOT_REVIEWED',
        whole_file=result['whole_file'], source_identity=sources, runtime=result['runtime'],
        execution_status=result['status'], accepted_originals=[575, 535], ledger=[21, 12],
        collector_reused=dict(checks=123, killed_faults=17, packet=str(prior / 'packet.json'),
                              sha256=c.sha(prior / 'packet.json')),
        compile_stop=result['ordered']['stop'], crossload_stop=None,
        target_load=False, boot=False, slot_credit=False,
        native_inputs=c.sha(c.STORE / 'macos-u1-inputs/pins.json'))
    roots = dict(execution=execution, native=native, readers=readers, corpus=corpus,
                 development=development)
    for path in roots.values(): storage.workspace(path)
    product.module('level1_retain', HERE.parent / 'loader-chain/retain.py').retain(
        c, destination, roots, 'STAGE1-LOADER-LEVEL1-R2', record)
    for path in roots.values(): shutil.rmtree(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'native', 'readers', 'corpus', 'development'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = vars(parser.parse_args())
    with storage.lease([p for n, p in args.items() if n != 'destination']):
        retain(**args)
