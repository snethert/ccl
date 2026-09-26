"""Run the shared ordered compiler with this packet's pinned proposal."""
from pathlib import Path
import sys
import product
import storage

if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        product.module('chain_ordered', product.HERE.parent / 'loader-chain/ordered.py').run(
            Path(sys.argv[1]).resolve(), product)
