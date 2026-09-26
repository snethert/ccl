"""Compile and cross-load the repaired stack through the shared producer."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
config = product.module('gc_config', HERE.parent / 'loader-chain/config.py')


def witnesses():
    return config.witnesses() + [HERE.parent / 'loader-fasl/witnesses/fasl.lisp'] + sorted((HERE / 'witnesses').glob('*.lisp'))


def inputs():
    paths = witnesses() + [HERE / n for n in ('product.py', 'run.py', 'files/parent.json', 'files/proposal.patch', 'counter.md', 'counter-schema.json')]
    paths += [HERE.parent / 'loader-chain' / n for n in ('build.py', 'ordered.lisp', 'support.lisp', 'load.lisp', 'patch.py', 'config.py')]
    paths += [HERE.parent / 'loader-level0' / n for n in ('prefix.lisp', 'package-first.lisp', 'package-second.lisp')]
    paths += [HERE.parent / 'loader-fasl/scratch.lisp', HERE.parent / 'registration/load.lisp', HERE.parent / 'bootstrap-validation/common.py']
    return {str(p.relative_to(product.c.ROOT)): product.c.sha(p) for p in paths}


def run(out):
    identity = inputs()
    assert not out.exists(), 'producer needs a fresh output directory'
    result = product.module('gc_build', HERE.parent / 'loader-chain/build.py').run(
        out, product, witnesses(), identity, checks=[HERE.parent / 'loader-fasl/scratch.lisp'])
    assert inputs() == identity
    product.c.save(out / 'producer-files.json', product.c.inventory(out))
    print(result['whole_file'])


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]): run(Path(sys.argv[1]).resolve())
