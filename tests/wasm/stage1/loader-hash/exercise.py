from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
build = product.module('packet_build', HERE / 'run.py')


def cases():
    c = product.c
    result = c.read(HERE.parent / 'loader-level0/prefix-cases.json')
    for name,args in [('packages', []), ('basic', []), ('promote', []), ('allocate', [5]),
                       ('cleanup', [12000]), ('hold', []), ('release', [])]:
        result.append(dict(id='rwlock-' + name, call=['CCL', 'LOADER-RWLOCK-' + name.upper()], args=args))
    for name in ('matrix', 'cube', 'chain', 'vector-chain', 'ranks', 'bits', 'string', 'integers', 'evaluation', 'collection', 'hold', 'release'):
        result.append(dict(id='array-' + name, call=['CCL', 'LOADER-ARRAY-' + name.upper()], args=[]))
    result += product.module('definitions_cases', HERE.parent / 'loader-def/exercise.py').cases()
    result += c.read(HERE / 'cases.json')
    return result


def run(out):
    identity = build.inputs()
    execution_inputs = {str(p.relative_to(product.c.ROOT)): product.c.sha(p)
        for folder in ('loader-chain', 'loader-hash', 'loader', 'loader-level0', 'loader-locks', 'loader-aref', 'loader-new-ptr', 'loader-def', 'bootstrap-validation')
        for p in product.c.files(HERE.parent / folder)
        if p.suffix in ('.py', '.mjs', '.json', '.lisp', '.patch')}
    product.c.save(out / 'execution-inputs.json', execution_inputs)
    result = product.module('chain_exercise', HERE.parent / 'loader-chain/exercise.py').run(
        out, product, cases(), build.witnesses(), sorted((HERE / 'controls').glob('*.mjs')), identity,
        product.c.read(HERE / 'startup-refusals.json'), product.c.read(HERE / 'pending-cases.json'))
    assert build.inputs() == identity
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
