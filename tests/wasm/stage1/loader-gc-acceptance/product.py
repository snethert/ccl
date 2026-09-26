"""Read the integrated audit-183 sources, bound to reviewed qualification."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
sys.path.append(str(HERE.parent / 'loader'))
import common as c
RECORD = c.ROOT / 'doc/WASM/stage1/integration-loader-gc.json'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def read(root, name):
    path = root / name
    if path.is_file():
        return c.read(path)
    return json.loads(gzip.decompress(path.with_name(path.name + '.gz').read_bytes()))


def check():
    record = c.read(RECORD)
    assert record['status'] == 'ACCEPTED_AND_INTEGRATED'
    review = record['review']
    assert hashlib.sha256((c.ROOT / review['path']).read_bytes()[:review['bytes']]).hexdigest() == review['sha256']
    packet = c.STORE / record['packet']['path']
    assert c.sha(packet / 'packet.json') == record['packet']['sha256']
    inventory = c.read(packet / 'packet.json')['files']
    for name, digest in record['packet']['records'].items():
        assert c.sha(packet / name) == digest == inventory[name]
    summary = c.read(packet / 'summary.json')
    assert record['all_sources'] == summary['all_proposal_sources']
    assert record['source_identity'] == summary['source_identity']
    assert record['runtime'] == summary['runtime']
    c.verify_files(c.ROOT, record['all_sources'])
    c.verify_files(c.ROOT, record['runtime_identity'])
    native = c.read(packet / 'native/qualification.json')
    assert native['source_identity'] == record['source_identity']
    assert c.read(packet / 'native/results/run.json')['status'] == 'PASS'
    readers = c.read(packet / 'readers/summary.json')
    assert readers['status'] == 'PASS' and readers['comparisons'] == 102
    assert all(record['source_identity'][n] == r['after'] for n, r in readers['full_sources'].items())
    corpus = c.read(packet / 'corpus/regression.json')
    assert corpus['status'] == 'PASS' and corpus['fresh_comparisons'] == 26048
    assert corpus['runtime'] == record['runtime']
    assert c.read(packet / 'corpus/cold-compiler.json')['environment']['ready_compiler']['sources'] == record['source_identity']
    collector = c.read(packet / 'collector/summary.json')
    assert collector['status'] == 'PASS' and collector['runtime'] == record['runtime']
    assert len(collector['mutants']) == 10 and all(r['status'] == 'KILLED' for r in collector['mutants'])
    return record


def sources():
    return {n: (c.ROOT / n).read_text() for n in check()['source_identity']}


def prepare_runtime(out):
    out.mkdir(parents=True, exist_ok=True)
    for path in (c.ROOT / 'runtime/wasm32').glob('*.mjs'):
        shutil.copyfile(path, out / path.name)


def runtime(out):
    record = check()
    out.mkdir(parents=True, exist_ok=True)
    module('integrated_runtime', HERE.parent / 'loader/run.py').runtime(out)
    actual = dict(source=c.sha(c.ROOT / 'runtime/wasm32/collector.c'),
                  binary=c.sha(out / 'collector.wasm'),
                  owner=c.sha(c.ROOT / 'runtime/wasm32/collector-owner.mjs'),
                  gc_count=dict(offset=204, maximum=536870911,
                      contract=c.sha(HERE.parent / 'loader-gc/counter.md'),
                      schema=c.sha(HERE.parent / 'loader-gc/counter-schema.json')))
    assert actual == record['runtime']
    c.save(out / 'array-runtime.json', actual)


def prepare_execution_runtime(base, environment):
    for name in ('owner-check/owner.mjs', 'runtime/collector-owner.mjs'):
        shutil.copyfile(c.ROOT / 'runtime/wasm32/collector-owner.mjs', base / name)
        environment['files'][name] = c.sha(base / name)


if __name__ == '__main__':
    record = check()
    print(dict(status='PASS', integrated_files=len(record['files']),
               qualified_sources=len(record['source_identity']), new_execution=False))
