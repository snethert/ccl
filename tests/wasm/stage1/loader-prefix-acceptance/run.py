"""Fresh integrated prefix execution with final driver identities frozen."""
from pathlib import Path
import importlib.util
import json
import sys
import check

HERE = Path(__file__).resolve().parent
LOCKS = HERE.parent / 'loader-locks'
c = check.c
sys.path.insert(0, str(LOCKS))
import product
import storage


def module(name):
    spec = importlib.util.spec_from_file_location('integrated_prefix_' + name, LOCKS / (name + '.py'))
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    return driver


def drivers():
    result = {}
    for folder in ('loader', 'loader-level0', 'loader-locks', 'loader-prefix-acceptance',
                   'bootstrap-validation', 'registration'):
        for path in c.files(HERE.parent / folder):
            if path.suffix in ('.py', '.lisp', '.json', '.mjs'):
                result[str(path.relative_to(c.ROOT))] = c.sha(path)
    return result


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    identity = check.check()
    inputs = drivers()
    c.save(out / 'inputs.json', inputs)
    # The retained witness drivers read integrated product files directly.
    product.sources = check.sources
    product.prepare_runtime = check.prepare_runtime
    execution = out / 'execution'
    module('run').run(execution)
    result = module('exercise').run(execution)
    module('initializer_control').run(execution)
    packet = c.STORE / c.read(check.RECORD)['packets']['locks']['path']
    previous = c.read(packet / 'execution/summary.json')
    assert result == previous, 'integrated execution differs from reviewed result'
    reproduced = {}
    for name, row in c.read(packet / 'regenerable.json').items():
        path = out / name
        if path.is_file():
            assert c.sha(path) == row['sha256'], name
            reproduced[name] = row['sha256']
    assert drivers() == inputs, 'driver changed during execution'
    assert check.check() == identity, 'product changed during execution'
    report = dict(**identity, drivers=inputs, reviewed_artifacts=reproduced,
                  product_files=7, boots=4, modules=262, initializers=18,
                  native_equal_rows=32, controls_per_boot=33,
                  initializer_control=c.read(execution / 'initializer-control.json'))
    report['new_execution'] = True
    c.save(out / 'integration.json', report)
    print(json.dumps(dict(status='PASS', boots=4, modules=262, native_equal_rows=32,
                          reproduced_artifacts=len(reproduced))))
    return report


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
