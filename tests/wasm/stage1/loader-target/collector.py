"""Qualify the new package scanner alongside the existing owner/weak cases."""
from pathlib import Path
import sys
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('target_product', HERE.parent / 'loader-level1/product.py')
product = importlib.util.module_from_spec(spec)
spec.loader.exec_module(product)
sys.modules['product'] = product
import storage

if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        product.module('target_collector', HERE.parent / 'loader-gc/collector.py').run(
            out, product,
            extra_cases=(HERE.parent / 'loader-level1/weak-collector-cases.mjs',
                         HERE / 'package-collector-cases.mjs'),
            extra_mutants=(('PACKAGE-COUNT', '    if(n!=8)return reject(s,BAD_OBJECT);', '',
                            'package-wrong-count-9'),))
