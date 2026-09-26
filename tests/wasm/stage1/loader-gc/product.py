"""Audit-182 repair delta over the pinned hash/FASL stack."""
from pathlib import Path
import hashlib
import importlib.util
import shutil
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


def parent_sources():
    parent = c.read(HERE / 'files/parent.json')
    c.verify_files(c.ROOT, parent['inputs'])
    bodies = module('fasl_parent', c.ROOT / parent['provider']).all_sources()
    bodies.update({n: (c.ROOT / n).read_text() for n in parent['extras']})
    assert {n: hashlib.sha256(b.encode()).hexdigest() for n, b in bodies.items()} == parent['sources']
    return bodies


def all_sources():
    return module('repair_patch', HERE.parent / 'loader-chain/patch.py').apply(
        parent_sources(), HERE / 'files/proposal.patch')


def sources():
    return {n: b for n, b in all_sources().items() if n.endswith('.lisp')}


def prepare_runtime(out):
    module('hash_parent_runtime', HERE.parent / 'loader-hash/product.py').prepare_runtime(out)
    (out / 'collector-owner.mjs').write_text(all_sources()['runtime/wasm32/collector-owner.mjs'])


def runtime(out):
    module('hash_parent_runtime', HERE.parent / 'loader-hash/product.py').runtime(out)
    bodies = all_sources()
    source = out / 'collector.c'
    source.write_text(bodies['runtime/wasm32/collector.c'])
    c.command(['/usr/local/opt/llvm/bin/clang', '--target=wasm32', '-O2', '-nostdlib', '-fno-builtin',
        '-matomics', '-mbulk-memory', '-Wl,--no-entry', '-Wl,--import-memory',
        '-Wl,--max-memory=2147549184', '-Wl,--shared-memory', '-Wl,--global-base=1048576',
        '-Wl,-z,stack-size=65536', '-Wl,--export=collect', '-Wl,--export=__stack_pointer',
        source, '-o', out / 'collector.wasm'], out / 'collector-build.log')
    owner = bodies['runtime/wasm32/collector-owner.mjs']
    (out / 'collector-owner.mjs').write_text(owner)
    row = dict(source=c.sha(source), binary=c.sha(out / 'collector.wasm'))
    row['owner'] = c.sha(out / 'collector-owner.mjs')
    row['gc_count'] = dict(offset=204, maximum=536870911, contract=c.sha(HERE / 'counter.md'),
                           schema=c.sha(HERE / 'counter-schema.json'))
    c.save(out / 'array-runtime.json', row)


def prepare_execution_runtime(base, environment):
    for name in ('owner-check/owner.mjs', 'runtime/collector-owner.mjs'):
        path = base / name
        path.write_text(all_sources()['runtime/wasm32/collector-owner.mjs'])
        environment['files'][name] = c.sha(path)
