"""Qualify the final source unit and its inherited array runtime once."""
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import product
import storage
import proposal

HERE = product.HERE
c = product.c


def run(kind, out):
    proposal.sources = product.sources
    if kind == 'readers':
        driver = product.module('ptr_readers', HERE.parent / 'namespace-consumers/readers.py')
        driver.proposal = SimpleNamespace(sources=lambda: {
            name: body for name, body in product.sources().items()
            if name in ('level-0/l0-bignum32.lisp', 'level-0/l0-cfm-support.lisp')})
        return driver.run(out)
    driver = product.module('ptr_' + kind, HERE.parent / 'loader' /
                            ('r6.py' if kind == 'native' else 'corpus.py'))
    if kind == 'native':
        driver.BRANCH = [str(p.relative_to(HERE / 'files')) for p in (HERE / 'files').rglob('*.lisp')]
        return driver.run(out)
    import execute
    from prepare import prepare
    product.runtime(out / 'runtime')

    def proposed(base):
        result = prepare(base)
        shutil.copyfile(out / 'runtime/collector.wasm', base / 'collector.wasm')
        env = c.read(base / 'execution-environment.json')
        env['files']['collector.wasm'] = c.sha(base / 'collector.wasm')
        env['array_runtime'] = c.read(out / 'runtime/array-runtime.json')
        c.save(base / 'execution-environment.json', env)
        return result

    execute.prepare = proposed
    result = driver.run(out)
    report = c.read(out / 'regression.json')
    report['runtime'] = c.read(out / 'runtime/array-runtime.json')
    c.save(out / 'regression.json', report)
    return result


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, path = sys.argv[1:]
    assert kind in ('native', 'corpus', 'readers')
    with storage.lease([Path(path)]):
        print(run(kind, Path(path).resolve()))
