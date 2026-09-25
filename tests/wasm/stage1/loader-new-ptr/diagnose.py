"""Retain the unrepresentable literal at the next ordered compiler boundary."""
from pathlib import Path
from types import SimpleNamespace
import sys
import product
import storage

def sources():
    bodies = product.sources()
    key = 'compiler/WASM32/wasm32-backend.lisp'
    anchor = '(t (refuse :heap-constant))'
    assert bodies[key].count(anchor) == 1
    bodies[key] = bodies[key].replace(anchor, '(t (format t "~&REFUSED-LITERAL ~s ~s~%" (type-of (first args)) (first args)) (refuse :heap-constant))')
    return bodies

if __name__ == '__main__':
    driver = product.module('diagnostic_ordered', product.HERE.parent / 'loader-locks/ordered.py')
    driver.product = SimpleNamespace(sources=sources)
    with storage.lease([Path(sys.argv[1])]):
        driver.run(Path(sys.argv[1]).resolve())
