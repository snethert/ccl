"""Compile and cross-load whole files using the shared producer."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
config = product.module('chain_config', HERE.parent / 'loader-chain/config.py')


def witnesses():
    return config.witnesses() + sorted((HERE / 'witnesses').glob('*.lisp'))


def inputs():
    paths = witnesses() + [HERE / name for name in
        ('product.py', 'run.py', 'scratch.lisp', 'files/parent.json', 'files/proposal.patch')]
    paths += [HERE.parent / 'loader-chain' / name for name in
        ('build.py', 'ordered.lisp', 'support.lisp', 'load.lisp', 'patch.py', 'config.py')]
    paths += [HERE.parent / 'loader-level0' / name for name in
        ('prefix.lisp', 'package-first.lisp', 'package-second.lisp')]
    paths += [HERE.parent / 'registration/load.lisp', HERE.parent / 'bootstrap-validation/common.py']
    return {str(p.relative_to(product.c.ROOT)): product.c.sha(p) for p in paths}


def run(out):
    identity = inputs()
    result = product.module('chain_build', HERE.parent / 'loader-chain/build.py').run(
        out, product, witnesses(), identity, checks=[HERE / 'scratch.lisp'])
    assert identity == inputs()
    print(result)
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
