"""Qualify this exact compiler/target proposal with R6/R6a or the full corpus."""
from pathlib import Path
import sys
import product
import storage
import proposal


def run(kind, out):
    proposal.sources = product.sources
    driver = product.module('aref_' + kind, product.HERE.parent / 'loader' /
                            ('r6.py' if kind == 'native' else 'corpus.py'))
    if kind == 'native':
        driver.BRANCH = ['compiler/WASM32/wasm32-backend.lisp', 'level-0/WASM32/w32-lap.lisp']
    return driver.run(out)


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, path = sys.argv[1:]
    assert kind in ('native', 'corpus')
    with storage.lease([Path(path)]):
        run(kind, Path(path).resolve())
