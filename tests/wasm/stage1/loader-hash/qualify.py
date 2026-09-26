"""Qualify the selected sources using shared drivers' declared inputs."""
from pathlib import Path
import hashlib
import shutil
import sys
import product
import storage

HERE = product.HERE
c = product.c


def run(kind, out):
    out.mkdir(parents=True, exist_ok=True)
    bodies = product.sources()
    changed = {n:b for n,b in bodies.items() if b != (c.ROOT / n).read_text()}
    if kind == 'native':
        return product.module('chain_r6', HERE.parent / 'loader/r6.py').run(
            out, product.sources, sorted(changed))
    if kind == 'readers':
        driver = product.module('chain_readers', HERE.parent / 'namespace-consumers/readers.py')
        selected = {n:b for n,b in changed.items() if n.startswith('level-0/') and '/WASM32/' not in n}
        # The native hash reader uses HASHENV's read-time constants.
        prelude = '(in-package "CCL")\n(require "HASHENV" "ccl:xdump;hashenv")'
        return driver.run(out, lambda:selected, prelude)
    assert kind == 'corpus'
    product.runtime(out / 'runtime')
    runtime = c.read(out / 'runtime/array-runtime.json')
    def prepare_execution(base):
        from prepare import prepare
        result = prepare(base)
        product.module('chain_metadata', HERE.parent / 'loader-def/metadata.py').overlay(base)
        shutil.copyfile(out / 'runtime/collector.wasm', base / 'collector.wasm')
        env = c.read(base / 'execution-environment.json')
        env['files']['collector.wasm'] = runtime['binary']
        env['array_runtime'] = runtime
        c.save(base / 'execution-environment.json', env)
        return result
    product.module('chain_corpus', HERE.parent / 'loader/corpus.py').run(
        out, product.sources, prepare_execution, runtime,
        "(dolist (name '(ccl::%map-areas ccl::%map-lfuns)) (pushnew name wasm32-compiler::*funcallable-deferred-inputs*))")
    assert c.read(out / 'base/execution-environment.json')['files']['collector.wasm'] == runtime['binary']
    result = c.read(out / 'regression.json'); result['runtime'] = runtime
    result['native_skips'] = {name: 'Target requires collector-owner enumeration; native heap walk has no matching target operation.' for name in ('CCL::%MAP-AREAS', 'CCL::%MAP-LFUNS')}
    c.save(out / 'regression.json', result)
    return result


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, destination = sys.argv[1:]
    with storage.lease([Path(destination)]):
        result = run(kind, Path(destination).resolve())
        print(kind, 'PASS')
