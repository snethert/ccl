"""Append FASL parser witnesses and controls to the shared execution."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
build = product.module('fasl_build', HERE / 'run.py')


def cases():
    return build.config.cases(product) + product.c.read(HERE / 'cases.json')


def run(out):
    identity = build.inputs()
    files = [p for folder in ('loader-chain', 'loader-fasl', 'loader-hash', 'loader',
        'loader-level0', 'loader-locks', 'loader-aref', 'loader-new-ptr', 'loader-def', 'bootstrap-validation')
        for p in product.c.files(HERE.parent / folder)
        if p.suffix in ('.py', '.mjs', '.json', '.lisp', '.patch')]
    execution_inputs = {str(p.relative_to(product.c.ROOT)): product.c.sha(p) for p in files}
    product.c.save(out / 'execution-inputs.json', execution_inputs)
    controls = sorted((HERE.parent / 'loader-hash/controls').glob('*.mjs')) + sorted((HERE / 'controls').glob('*.mjs'))
    result = product.module('chain_exercise', HERE.parent / 'loader-chain/exercise.py').run(
        out, product, cases(), build.witnesses(), controls, identity,
        product.c.read(HERE / 'startup-refusals.json'),
        {**product.c.read(HERE.parent / 'loader-hash/pending-cases.json'),
         **product.c.read(HERE / 'pending-cases.json')})
    assert build.inputs() == identity
    product.c.verify_files(product.c.ROOT, execution_inputs)
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
