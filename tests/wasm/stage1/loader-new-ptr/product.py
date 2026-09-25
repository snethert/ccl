"""Native MPN boundary over the general-array loader proposal."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('array_product', HERE.parent / 'loader-aref/product.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
c = parent.c
module = parent.module
runtime = parent.runtime
prepare_runtime = parent.prepare_runtime


def sources():
    bodies = parent.sources()
    for path in (HERE / 'files').rglob('*.lisp'):
        bodies[str(path.relative_to(HERE / 'files'))] = path.read_text()
    return bodies
