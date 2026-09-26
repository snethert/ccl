"""Current checkout sources for ordered level-1 work."""
from pathlib import Path
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


def sources():
    names = set(c.read(c.ROOT / 'doc/WASM/stage1/integration-loader-gc.json')['source_identity'])
    names.update(('level-1/l1-boot-1.lisp', 'level-1/l1-boot-2.lisp', 'level-1/l1-init.lisp'))
    return {name: (c.ROOT / name).read_text() for name in sorted(names)}


def runtime(out):
    out.mkdir(parents=True, exist_ok=True)
    module('level1_runtime', HERE.parent / 'loader/run.py').runtime(out)
    record = c.read(c.ROOT / 'doc/WASM/stage1/integration-loader-gc.json')
    c.verify_files(c.ROOT, record['runtime_identity'])
    assert c.sha(out / 'collector.wasm') == record['runtime']['binary']
    c.save(out / 'array-runtime.json', record['runtime'])


def prepare_runtime(out):
    return module('level1_runtime_prepare', HERE.parent / 'loader-gc-acceptance/product.py').prepare_runtime(out)


def prepare_execution_runtime(base, environment):
    return module('level1_runtime_execution', HERE.parent / 'loader-gc-acceptance/product.py').prepare_execution_runtime(base, environment)
