"""Count original executions, with exact final-source and reader bindings."""
from pathlib import Path
import json
import sys
import tarfile
import backend

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def read(path):
    return json.loads(path.read_text())

def names(rows):
    return {r['definition'] for r in rows if not r.get('targetOnly') and not r.get('nativeCounterpart')
            and not r['definition'].startswith('CORE-')
            and r['definition'] not in {'EQL', 'FULLTAG', 'LISPTAG', 'TYPECODE', 'ASSQ'}}

def summarize(numeric, environment, native):
    packet = ROOT.parent / 'ccl-evidence/2026-09-22-stage1-bootstrap-numeric-dispatch-r1'
    with tarfile.open(packet / 'artifacts.tar.gz') as archive:
        previous = names(json.load(archive.extractfile('numeric/compiled/native.json')))
    rows = read(numeric / 'compiled/native.json')
    assert sum(r['definition'] == 'CORE-POSITIVE-FIXNUM-PRODUCT' for r in rows) == 28
    assert sum(r['definition'].startswith('CORE-FLOAT-SIGN-') for r in rows) == 8
    current = names(rows)
    assert previous <= current
    assert {'MULTIPLY-BIGNUMS', '%DOUBLE-FLOAT-MINUSP', '%SHORT-FLOAT-MINUSP'} <= current
    workers = read(numeric / 'execution.json')['rows']
    assert len(workers) == 2 and sum(w['comparisons'] for w in workers) == 4 * len(rows)
    report = read(native / 'run.json')
    assert report['status'] == 'PASS' and report['registered_tests']['passed'] == 21843
    assert report['restored_fasls'] == 164 and report['source_restored']
    for name, text in {backend.BACKEND: backend.generate(), backend.ARCH: backend.arch(),
                       **backend.source_files(ROOT)}.items():
        for directory in (native / 'proposal', numeric / 'compiled/proposal', environment / 'proposal'):
            assert (directory / 'files' / name).read_text() == text, (name, directory)
    for source in HERE.glob('*.lisp'):
        copied = numeric / 'driver' / source.name
        if copied.exists():
            assert copied.read_bytes() == source.read_bytes(), source.name
    assert (numeric / 'bignum-check.mjs').read_bytes() == (HERE / 'bignum-check.mjs').read_bytes()
    reader_rows = read(numeric / 'reader-proof/readers.json')
    assert len(reader_rows) == 8 and all(r['equal'] for r in reader_rows)
    assert all(r['forms'] > 1 for r in reader_rows[4:])
    whole = read(numeric / 'compiled/whole-file.json')
    installed = {m['name'] for m in read(numeric / 'compiled/modules.json')}
    proof = []
    for name in sorted(current - previous):
        matches = [r for r in whole if r['name'] == name and r['module'] in installed]
        assert len(matches) == 1, (name, matches)
        proof.append(dict(name=name, file=matches[0]['file'], module=matches[0]['module'],
                          cases=sum(r['definition'] == name for r in rows)))
    (numeric / 'source-proof.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    admitted = read(environment / 'summary.json')['old_cohort']
    result = dict(status='PASS', original_definitions_executed=len(current),
                  non_nil_witness=len({r['definition'] for r in rows if r['definition'] in current
                    and not r.get('caught') and any(v is not None for v in r['values'])}),
                  new_executions=sorted(current - previous), admitted=admitted['admitted'],
                  denominator=admitted['definitions'], native_rows=len(rows),
                  comparisons=sum(w['comparisons'] for w in workers),
                  direct_checks=sum(len(w['bignums']) for w in workers),
                  collections_during_calls=sum(w['internalCollections'] for w in workers),
                  retry_collections=sum(w['retryCollections'] for w in workers),
                  structural_collector_checks=read(numeric / 'istruct-checks.json')['checks'],
                  native_tests=21843, restored_fasls=164, reader_assignments=8,
                  scope='Original bignum multiplication and float MINUSP helpers execute. Generic MINUSP and mixed bignum/fixnum multiplication still need %KERNEL-RESTART. The target fixnum loop is checked separately against native products. Division/GCD primitives, further metadata and image/READY work remain unfinished; no LL15 credit.')
    (numeric / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    summarize(*(Path(p).resolve() for p in sys.argv[1:]))
