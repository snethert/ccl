"""Compare the two changed files under every existing-target reader."""
from pathlib import Path
import importlib.util
import subprocess
import sys
from types import SimpleNamespace
import product
import storage

HERE = Path(__file__).resolve().parent
c = product.c


def run(out, mutant=False):
    names = ['level-0/l0-aprims.lisp', 'level-0/l0-misc.lisp']
    bodies = {n: product.sources()[n] for n in names}
    if mutant:
        key = names[0]
        anchor = '#-wasm32-target\n(defun %revive-system-locks '
        assert bodies[key].count(anchor) == 1
        bodies[key] = bodies[key].replace(anchor, '#+wasm32-target\n(defun %revive-system-locks ')
    spec = importlib.util.spec_from_file_location('lock_readers', HERE.parent / 'namespace-consumers/readers.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.proposal = SimpleNamespace(sources=lambda: bodies)
    return driver.run(out)


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        print(run(out / 'positive')['status'])
        try:
            run(out / 'mutant', True)
        except subprocess.CalledProcessError:
            assert 'Existing-target reader changed:' in (out / 'mutant/run.log').read_text()
            c.save(out / 'mutant.json', dict(status='KILLED', mutation='native revival reader guard inverted'))
        else:
            raise AssertionError('reader mutant survived')
