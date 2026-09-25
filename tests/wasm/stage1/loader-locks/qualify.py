"""Required native qualification and unchanged-compiler regression."""
from pathlib import Path
import importlib.util
import sys
import product
import storage

HERE = Path(__file__).resolve().parent


def run(kind, out):
    product.parent.accepted.sources = product.sources
    spec = importlib.util.spec_from_file_location('locks_' + kind,
        HERE.parent / 'loader' / ('r6.py' if kind == 'native' else 'corpus.py'))
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    if kind == 'native':
        driver.BRANCH = ['level-0/l0-aprims.lisp', 'level-0/l0-misc.lisp']
    return driver.run(out)


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, path = sys.argv[1:]
    assert kind in ('native', 'corpus')
    with storage.lease([Path(path)]):
        run(kind, Path(path).resolve())
