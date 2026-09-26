"""Extend the shared loader with hash and I/O witnesses."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE


def witnesses():
    return [HERE.parent / folder / name for folder, name in (
        ('loader-level0', 'packages.lisp'), ('loader-locks', 'locks.lisp'),
        ('loader-aref', 'arrays.lisp'), ('loader-new-ptr', 'witnesses.lisp'),
        ('loader-def', 'witnesses.lisp'))] + sorted((HERE / 'witnesses').glob('*.lisp'))


def inputs():
    # Compilation identity excludes independent execution and retention tools.
    c = product.c
    paths = witnesses() + [HERE / 'product.py', HERE / 'run.py',
        HERE / 'files/parent.json', HERE / 'files/proposal.patch']
    paths += [HERE.parent / 'loader-chain' / name for name in
              ('build.py', 'ordered.lisp', 'support.lisp', 'load.lisp')]
    paths += [HERE.parent / 'loader-level0' / name for name in
              ('prefix.lisp', 'package-first.lisp', 'package-second.lisp')]
    paths += [HERE.parent / 'registration/load.lisp',
              HERE.parent / 'bootstrap-validation/common.py']
    return {str(p.relative_to(c.ROOT)): c.sha(p) for p in paths}


def run(out):
    identity = inputs()
    result = product.module('chain_build', HERE.parent / 'loader-chain/build.py').run(
        out, product, witnesses(), identity)
    assert identity == inputs()
    print(result)
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
