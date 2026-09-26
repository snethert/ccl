"""Compile level-0 and then the real ordered level-1 module list."""
from pathlib import Path
import sys
import product
import storage

if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        product.module('level1_ordered', product.HERE.parent / 'loader-chain/ordered.py').run(
            out, product, level1='only' if '--level1-only' in sys.argv else True)
