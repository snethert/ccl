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
    for name in ('execution.log', 'execution-environment.json', 'execution-plan.json',
                 'execution-report.json', 'execution-report.identity.json'):
        if (base / name).exists():
            shutil.copyfile(base / name, out / ('before-runtime-' + name))
    if (out / 'regression.json').exists():
        shutil.copyfile(out / 'regression.json', out / 'before-runtime-regression.json')
    product.runtime(out / 'array-runtime')
    import execute
    from prepare import prepare
    expected = c.read(c.PARENT / 'deterministic.json')

    def proposed(base):
        # PREPARE verifies the immutable prerequisite service before our overlay.
        with tarfile.open(c.PARENT / 'execution.tar.gz') as archive:
            data = archive.extractfile('collector.wasm').read()
            (base / 'metadata-check.mjs').write_bytes(archive.extractfile('metadata-check.mjs').read())
        (base / 'collector.wasm').write_bytes(data)
        assert c.sha(base / 'collector.wasm') == expected['collector.wasm']
        result = prepare(base)
        product.module('definition_metadata', product.HERE / 'metadata.py').overlay(base)
        shutil.copyfile(out / 'array-runtime/collector.wasm', base / 'collector.wasm')
        env = c.read(base / 'execution-environment.json')
        env['files']['collector.wasm'] = c.sha(base / 'collector.wasm')
        env['array_runtime'] = dict(source=c.read(out / 'array-runtime/array-runtime.json')['source'],
                                   driver=c.sha(Path(__file__)))
        c.save(base / 'execution-environment.json', env)
        return result

    execute.prepare = proposed
    result = execute.execute(base, 4, 'full')
    result['runtime'] = c.read(out / 'array-runtime/array-runtime.json')
    result['compiler_reuse'] = c.sha(out / 'cold-compiler.json')
    assert c.read(base / 'execution-environment.json')['files']['collector.wasm'] == result['runtime']['binary']
    c.save(out / 'regression.json', result)
    print(result)


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
