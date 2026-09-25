"""Observe the first ordered stop with the MPN boundary proposal."""
from pathlib import Path
import sys
import product
import storage

if __name__ == '__main__':
    driver = product.module('ptr_ordered', product.HERE.parent / 'loader-locks/ordered.py')
    driver.product = product
    with storage.lease([Path(sys.argv[1])]):
        driver.run(Path(sys.argv[1]).resolve())
