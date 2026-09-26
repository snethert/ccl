"""Preserve O-97 through the unrepaired parent's own producer and executor."""
from pathlib import Path
import sys
import product
import storage

if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        parent = product.module('unrepaired_product', product.HERE.parent / 'loader-fasl/product.py')
        config = product.module('baseline_config', product.HERE.parent / 'loader-chain/config.py')
        witnesses = config.witnesses() + [product.HERE.parent / 'loader-fasl/witnesses/fasl.lisp',
                                         product.HERE / 'witnesses/gc.lisp']
        inputs = {str(p.relative_to(product.c.ROOT)): product.c.sha(p)
                  for p in witnesses + [Path(__file__), product.HERE.parent / 'loader-fasl/files/proposal.patch']}
        product.module('baseline_build', product.HERE.parent / 'loader-chain/build.py').run(
            out, parent, witnesses, inputs, checks=[product.HERE.parent / 'loader-fasl/scratch.lisp'])
        cases = config.cases(product) + product.c.read(product.HERE.parent / 'loader-fasl/cases.json')
        cases += [dict(id='gc-fresh', call=['CCL', 'LOADER-GC-FRESH'], args=[])]
        pending = product.c.read(product.HERE.parent / 'loader-hash/pending-cases.json')
        pending.update(product.c.read(product.HERE.parent / 'loader-fasl/pending-cases.json'))
        pending['gc-fresh'] = 'O-97 original failure: missing callable %GET-GC-COUNT.'
        controls = [product.HERE.parent / name for name in
                    ['loader-hash/controls/buffers.mjs', 'loader-fasl/controls/fasl.mjs']]
        result = product.module('baseline_execution', product.HERE.parent / 'loader-chain/exercise.py').run(
            out, parent, cases, witnesses, controls, inputs,
            product.c.read(product.HERE.parent / 'loader-fasl/startup-refusals.json'), pending)
        for row in result['runs'].values():
            failure = next(r for r in row['failures'] if r['id'] == 'gc-fresh')
            assert failure['error'] == 'checked 10' and failure['native_expected'] == [None, None]
