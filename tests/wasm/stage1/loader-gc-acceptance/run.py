"""Replay the integrated sources through the shared loader drivers."""
from pathlib import Path
import sys
import product
import storage

c, HERE = product.c, product.HERE


def inputs():
    folders = ('loader-gc-acceptance', 'loader-chain', 'loader-gc', 'loader-fasl',
               'loader-hash', 'loader', 'loader-level0', 'loader-locks', 'loader-aref',
               'loader-new-ptr', 'loader-def', 'registration', 'bootstrap-validation')
    files = [p for folder in folders for p in c.files(HERE.parent / folder)
             if p.suffix in ('.py', '.mjs', '.json', '.lisp', '.patch', '.md')]
    return {str(p.relative_to(c.ROOT)): c.sha(p) for p in files + [product.RECORD]}


def run(out):
    assert not out.exists(), 'use a fresh output directory'
    record, pins = product.check(), inputs()
    config = product.module('integration_config', HERE.parent / 'loader-chain/config.py')
    witnesses = config.witnesses() + [HERE.parent / 'loader-fasl/witnesses/fasl.lisp']
    witnesses += sorted((HERE.parent / 'loader-gc/witnesses').glob('*.lisp'))
    cases = config.cases(product) + c.read(HERE.parent / 'loader-fasl/cases.json') + [
        dict(id='gc-fresh', call=['CCL', 'LOADER-GC-FRESH'], args=[]),
        dict(id='gc-constructor-flags', call=['CCL', 'LOADER-GC-CONSTRUCTOR-FLAGS'], args=[])]
    controls = [HERE.parent / n for n in ('loader-hash/controls/buffers.mjs', 'loader-fasl/controls/fasl.mjs')]
    controls += sorted((HERE.parent / 'loader-gc/controls').glob('*.mjs'))
    product.module('integration_build', HERE.parent / 'loader-chain/build.py').run(
        out, product, witnesses, pins, checks=[HERE.parent / 'loader-fasl/scratch.lisp'])
    result = product.module('integration_execute', HERE.parent / 'loader-chain/exercise.py').run(
        out, product, cases, witnesses, controls, pins,
        c.read(HERE.parent / 'loader-fasl/startup-refusals.json'),
        {**c.read(HERE.parent / 'loader-hash/pending-cases.json'),
         **c.read(HERE.parent / 'loader-fasl/pending-cases.json')})
    packet = c.STORE / record['packet']['path']
    previous = product.read(packet, 'execution/summary.json')
    assert result == previous, 'integrated execution differs from reviewed proposal'
    artifacts = {n.removeprefix('execution/'): r for n, r in c.read(packet / 'regenerable.json').items()
                 if n.startswith('execution/')}
    assert len(artifacts) == 3628
    for name, row in artifacts.items():
        assert c.sha(out / name) == row['sha256'], name
    assert inputs() == pins and product.check() == record
    c.save(out / 'integration.json', dict(status='PASS', new_execution=True,
        source_identity=record['source_identity'], runtime=record['runtime'],
        integration_record=c.sha(product.RECORD), drivers=pins,
        reviewed_artifacts_equal=len(artifacts), whole_file=result['whole_file'],
        native_tests_reused=21843, reader_comparisons_reused=102,
        collector_checks_reused=82, slot_credit=False))
    c.save(out / 'execution-files.json', c.inventory(out))
    print(dict(status='PASS', reviewed_artifacts_equal=len(artifacts), whole_file=result['whole_file']))


if __name__ == '__main__':
    destination = Path(sys.argv[1]).resolve()
    with storage.lease([destination]):
        if '--corpus' in sys.argv:
            sys.setrecursionlimit(20000)
            product.module('integration_qualify', HERE.parent / 'loader-chain/qualify.py').run('corpus', destination, product)
            print('corpus PASS')
        else:
            run(destination)
