"""Run the unchanged ordered compiler to its next real stop."""
from pathlib import Path
import sys
import product
import storage

if __name__ == '__main__':
    driver = product.module('aref_ordered', product.HERE.parent / 'loader-locks/ordered.py')
    driver.product = product
    with storage.lease([Path(sys.argv[1])]):
        driver.run(Path(sys.argv[1]).resolve())
