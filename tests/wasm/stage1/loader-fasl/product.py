"""Pinned delta over the hash/I/O proposal; shared product files stay untouched."""
from pathlib import Path
import hashlib
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
sys.path.append(str(HERE.parent / 'loader'))
import common as c


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def all_sources():
    parent = c.read(HERE / 'files/parent.json')
    c.verify_files(c.ROOT, parent['inputs'])
    bodies = module('hash_product', c.ROOT / parent['provider']).all_sources()
    assert {n: hashlib.sha256(b.encode()).hexdigest() for n, b in bodies.items()} == parent['sources']
    return module('proposal_patch', HERE.parent / 'loader-chain/patch.py').apply(
        bodies, HERE / 'files/proposal.patch')


def sources():
    return {n: b for n, b in all_sources().items() if n.endswith('.lisp')}


def prepare_runtime(out):
    module('hash_runtime', HERE.parent / 'loader-hash/product.py').prepare_runtime(out)


def runtime(out):
    module('hash_runtime', HERE.parent / 'loader-hash/product.py').runtime(out)
