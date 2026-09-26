"""Execute the inherited witnesses and the coherent collection-count protocol."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
build = product.module('gc_build_api', HERE / 'run.py')


def cases():
    return build.config.cases(product) + product.c.read(HERE.parent / 'loader-fasl/cases.json') + [
        dict(id='gc-fresh', call=['CCL', 'LOADER-GC-FRESH'], args=[]),
        dict(id='gc-constructor-flags', call=['CCL', 'LOADER-GC-CONSTRUCTOR-FLAGS'], args=[])]


def run(out):
    identity = build.inputs()
    product.c.verify_files(out, product.c.read(out / 'producer-files.json'))
    declared = set(product.c.read(out / 'producer-files.json')) | {'producer-files.json'}
    assert {str(p.relative_to(out)) for p in product.c.files(out)} == declared, 'undeclared producer output'
    folders = ('loader-gc', 'loader-chain', 'loader-fasl', 'loader-hash', 'loader', 'loader-level0',
               'loader-locks', 'loader-aref', 'loader-new-ptr', 'loader-def', 'bootstrap-validation')
    files = [p for folder in folders for p in product.c.files(HERE.parent / folder)
             if p.suffix in ('.py', '.mjs', '.json', '.lisp', '.patch')]
    pins = {str(p.relative_to(product.c.ROOT)): product.c.sha(p) for p in files}
    product.c.save(out / 'execution-inputs.json', pins)
    controls = [HERE.parent / n for n in ['loader-hash/controls/buffers.mjs', 'loader-fasl/controls/fasl.mjs']]
    controls += sorted((HERE / 'controls').glob('*.mjs'))
    result = product.module('gc_execute', HERE.parent / 'loader-chain/exercise.py').run(
        out, product, cases(), build.witnesses(), controls, identity,
        product.c.read(HERE.parent / 'loader-fasl/startup-refusals.json'),
        {**product.c.read(HERE.parent / 'loader-hash/pending-cases.json'),
         **product.c.read(HERE.parent / 'loader-fasl/pending-cases.json')})
    assert build.inputs() == identity
    product.c.verify_files(product.c.ROOT, pins)
    product.c.save(out / 'execution-files.json', product.c.inventory(out))
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]): run(Path(sys.argv[1]).resolve())
