"""Current checkout sources for ordered level-1 work."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
sys.path.append(str(HERE.parent / 'loader'))
import common as c

# Reuse the corpus's qualified callable EQL leaf for native hash constructors.
equality_leaf = True


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def sources():
    names = set(c.read(c.ROOT / 'doc/WASM/stage1/integration-loader-gc.json')['source_identity'])
    names.update(('level-1/l1-boot-1.lisp', 'level-1/l1-boot-2.lisp', 'level-1/l1-init.lisp',
                  'level-1/l1-numbers.lisp', 'level-1/l1-aprims.lisp', 'level-0/l0-numbers.lisp',
                  'level-1/l1-clos-boot.lisp', 'level-1/l1-dcode.lisp'))
    return {name: (c.ROOT / name).read_text() for name in sorted(names)}


def runtime(out):
    out.mkdir(parents=True, exist_ok=True)
    module('level1_runtime', HERE.parent / 'loader/run.py').runtime(out)
    # Runtime changes receive fresh collector evidence; do not claim the old binary.
    source = c.ROOT / 'runtime/wasm32/collector.c'
    (out / 'collector.c').write_bytes(source.read_bytes())
    c.save(out / 'array-runtime.json', dict(source=c.sha(source),
        binary=c.sha(out / 'collector.wasm'),
        owner=c.sha(c.ROOT / 'runtime/wasm32/collector-owner.mjs'),
        gc_count=dict(offset=204, maximum=536870911,
            contract=c.sha(HERE.parent / 'loader-gc/counter.md'),
            schema=c.sha(HERE.parent / 'loader-gc/counter-schema.json'))))


def prepare_runtime(out):
    return module('level1_runtime_prepare', HERE.parent / 'loader-gc-acceptance/product.py').prepare_runtime(out)


def prepare_execution_runtime(base, environment):
    return module('level1_runtime_execution', HERE.parent / 'loader-gc-acceptance/product.py').prepare_execution_runtime(base, environment)
