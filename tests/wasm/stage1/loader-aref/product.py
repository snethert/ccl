"""General array access proposal over the audit-180 integrated product."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prefix_identity', HERE.parent / 'loader-prefix-acceptance/check.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
c = parent.c
sys.path.insert(0, str(HERE.parent / 'loader'))


def sources():
    bodies = parent.sources()
    for path in (HERE / 'files').rglob('*.lisp'):
        bodies[str(path.relative_to(HERE / 'files'))] = path.read_text()
    return bodies


prepare_runtime = parent.prepare_runtime


def runtime(out):
    driver = module('aref_runtime', HERE.parent / 'loader/run.py')
    command = c.command
    def execute(argv, *args, **kwargs):
        argv = [HERE / 'files/runtime/wasm32/collector.c'
                if arg == c.ROOT / 'runtime/wasm32/collector.c' else arg for arg in argv]
        return command(argv, *args, **kwargs)
    c.command = execute
    try:
        driver.runtime(out)
    finally:
        c.command = command
    c.save(out / 'array-runtime.json', dict(
        source=c.sha(HERE / 'files/runtime/wasm32/collector.c'),
        binary=c.sha(out / 'collector.wasm')))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
