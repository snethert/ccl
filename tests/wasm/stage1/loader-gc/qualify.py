"""Native, reader and full compiler/runtime qualification for the repair."""
from pathlib import Path
import sys
import product
import storage

if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, destination = sys.argv[1:]
    with storage.lease([Path(destination)]):
        product.module('gc_qualifier', product.HERE.parent / 'loader-chain/qualify.py').run(
            kind, Path(destination).resolve(), product)
        print(kind, 'PASS')
