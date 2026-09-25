"""Use the established native and corpus gates with this exact proposal."""
from pathlib import Path
import importlib.util
import sys
import product as unit
import storage

HERE = Path(__file__).resolve().parent


def run(kind, out):
    unit.accepted.sources = unit.sources
    path = HERE.parent / 'loader' / ('r6.py' if kind == 'native' else 'corpus.py')
    spec = importlib.util.spec_from_file_location('level0_' + kind, path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    if kind == 'native':
        driver.BRANCH = [n for n in unit.c.read(HERE / 'provenance.json')['sources']
                         if n.endswith('.lisp')]
    return driver.run(out)


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, destination = sys.argv[1:]
    assert kind in ('native', 'corpus')
    with storage.lease([Path(destination)]):
        run(kind, Path(destination).resolve())
