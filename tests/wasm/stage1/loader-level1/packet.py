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
    assert result['whole_file'] == [29, 24, 0]
    c.verify_files(execution, c.read(execution / 'artifacts.json'))
    assert c.read(native / 'qualification.json')['source_identity'] == sources
    assert c.read(native / 'results/run.json')['status'] == 'PASS'
    matrix = c.read(readers / 'summary.json')
    assert matrix['status'] == 'PASS' and matrix['comparisons'] == 68
    assert all(sources[n] == r['after'] for n, r in matrix['full_sources'].items())
    regression = c.read(corpus / 'regression.json')
    assert regression['status'] == 'PASS' and regression['fresh_comparisons'] == 26048
    assert regression['runtime'] == result['runtime']
    assert c.read(corpus / 'cold-compiler.json')['environment']['ready_compiler']['sources'] == sources
    dispatch = c.read(execution / 'dispatch.json')
    assert dispatch['status'] == 'PASS' and len(dispatch['rows']) == 18
    assert all(r['dispatch'] and r['unchanged_input_skipped'] for r in dispatch['rows'])
    prior = c.read(c.ROOT / 'doc/WASM/stage1/integration-loader-gc.json')
    c.verify_files(c.ROOT, prior['runtime_identity'])
    assert result['runtime'] == prior['runtime']
    record = dict(status='IMPLEMENTED_AWAITING_REVIEW', review='NOT_REVIEWED',
        whole_file=result['whole_file'], source_identity=sources, runtime=result['runtime'],
        execution_status=result['status'], accepted_originals=[575, 535], ledger=[21, 12],
        collector_reused=dict(checks=82, killed_faults=10, packet=prior['packet']),
        compile_stop=result['ordered']['stop'], crossload_stop='level-1/l1-boot-2.lisp: SETF-FUNCTION-NAME',
        target_load=False, boot=False, slot_credit=False,
        native_inputs=c.sha(c.STORE / 'macos-u1-inputs/pins.json'))
    roots = dict(execution=execution, native=native, readers=readers, corpus=corpus,
                 development=development)
    for path in roots.values(): storage.workspace(path)
    product.module('level1_retain', HERE.parent / 'loader-chain/retain.py').retain(
        c, destination, roots, 'STAGE1-LOADER-LEVEL1-R1', record)
    for path in roots.values(): shutil.rmtree(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('destination', 'execution', 'native', 'readers', 'corpus', 'development'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = vars(parser.parse_args())
    with storage.lease([p for n, p in args.items() if n != 'destination']):
        retain(**args)
