"""Reexecute the complete corpus with the array collector; reuse compiler bytes."""
from pathlib import Path
import shutil
import sys
import tarfile
import product
import storage

c = product.c


def run(out):
    base = out / 'base'
    old = c.read(out / 'regression.json')
    assert old['status'] == 'PASS' and old['fresh_comparisons'] == 26048
    for name in ('execution-report.json', 'execution-report.identity.json'):
        shutil.copyfile(base / name, out / ('before-array-runtime-' + name))
    c.save(out / 'before-array-runtime-regression.json', old)
    product.runtime(out / 'array-runtime')
    import execute
    from prepare import prepare
    expected = c.read(c.PARENT / 'deterministic.json')

    def proposed(base):
        # PREPARE verifies the immutable prerequisite service before our overlay.
        with tarfile.open(c.PARENT / 'execution.tar.gz') as archive:
            data = archive.extractfile('collector.wasm').read()
        (base / 'collector.wasm').write_bytes(data)
        assert c.sha(base / 'collector.wasm') == expected['collector.wasm']
        result = prepare(base)
        shutil.copyfile(out / 'array-runtime/collector.wasm', base / 'collector.wasm')
        env = c.read(base / 'execution-environment.json')
        env['files']['collector.wasm'] = c.sha(base / 'collector.wasm')
        env['array_runtime'] = dict(source=c.sha(product.HERE / 'files/runtime/wasm32/collector.c'),
                                   driver=c.sha(Path(__file__)))
        c.save(base / 'execution-environment.json', env)
        return result

    execute.prepare = proposed
    result = execute.execute(base, 4, 'full')
    result['runtime'] = c.read(out / 'array-runtime/array-runtime.json')
    result['compiler_reuse'] = c.sha(out / 'cold-compiler.json')
    c.save(out / 'regression.json', result)
    print(result)


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
