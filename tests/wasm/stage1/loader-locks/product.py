"""Native lock boundary over the unintegrated SET-PACKAGE proposal."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'loader-level0'))
spec = importlib.util.spec_from_file_location('loader_level0_product', HERE.parent / 'loader-level0/product.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
c = parent.c


def sources():
    bodies = parent.sources()
    for path in (HERE / 'files').rglob('*.lisp'):
        bodies[str(path.relative_to(HERE / 'files'))] = path.read_text()
    return bodies


prepare_runtime = parent.prepare_runtime
