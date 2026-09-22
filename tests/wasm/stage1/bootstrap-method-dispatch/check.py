"""Check execution credit and bind the method-dispatch proposal's results."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT.parent / 'ccl-evidence/2026-09-22-stage1-bootstrap-gcd-r1'
sys.path.insert(0, str(HERE))
import backend


def original(rows):
    return {r['definition'] for r in rows if not r.get('targetOnly')
            and not r.get('nativeCounterpart') and not r['definition'].startswith('CORE-')
            and r['definition'] not in {'EQL', 'FULLTAG', 'LISPTAG', 'TYPECODE', 'ASSQ'}}


def check(out, native):
    read = lambda p: json.loads(p.read_text())
    for name in ('compile.lisp',):
        assert (out / 'driver' / name).read_bytes() == (out / 'compiled/source' / name).read_bytes(), name
    rows = read(out / 'compiled/native.json')
    with tarfile.open(BASE / 'artifacts.tar.gz') as archive:
        previous = original(json.load(archive.extractfile('numeric/compiled/native.json')))
    current = original(rows)
    assert previous <= current, sorted(previous - current)
    required = {'%%ASSQ-COMBINED-METHOD-DCODE', '%%ASSOC-COMBINED-METHOD-DCODE',
                'CORE-SELECTION-GENERIC', 'CORE-SELECTION-REBIND',
                'CORE-SELECTION-HEAP', 'CORE-SELECTION-LEXPR-EQ', 'CORE-SELECTION-LEXPR-EQL', 'CORE-SELECTION-ERROR'}
    whole = read(out / 'compiled/whole-file.json')
    modules = {r['name'] for r in read(out / 'compiled/modules.json')}
    source_proof = []
    for name in ('%%ASSQ-COMBINED-METHOD-DCODE', '%%ASSOC-COMBINED-METHOD-DCODE'):
        definitions = [r for r in whole if r['name'] == name and r['module'] in modules]
        assert len(definitions) == 1 and definitions[0]['file'] == 'ccl:level-1;l1-dcode.lisp'
        source_proof.append(definitions[0])
    counts = {name: sum(r['definition'] == name for r in rows) for name in required}
    assert all(counts.values()), counts
    symbols = {r['id']: r['name'] for r in read(out / 'compiled/symbols.json')}
    assert {symbols[r['values'][0]['symbol']] for r in rows
            if r['definition'] == '%%ASSQ-COMBINED-METHOD-DCODE'} == {'FIRST', 'SECOND', 'DEFAULT'}
    workers = read(out / 'execution.json')['rows']
    comparisons = sum(r['comparisons'] for r in workers)
    assert comparisons == 4 * len(rows)
    report = read(native / 'run.json')
    assert report['status'] == 'PASS' and report['registered_tests']['passed'] == 21843
    for name, text in {backend.parent.BACKEND: backend.generate(), backend.parent.ARCH: backend.arch(),
                       **backend.source_files(ROOT)}.items():
        assert (out / 'compiled/proposal/files' / name).read_text() == text, name
        assert (native / 'proposal/files' / name).read_text() == text, name
    summary = dict(status='PASS', original_definitions_executed=len(current),
                   non_nil_witness=len({r['definition'] for r in rows if r['definition'] in current
                     and not r.get('caught') and any(v is not None for v in r['values'])}),
                   new_executions=sorted(current - previous), source_proof=source_proof, cases=counts,
                   native_rows=len(rows), comparisons=comparisons, new_comparisons=4 * sum(counts.values()),
                   collections_during_calls=sum(r['internalCollections'] for r in workers),
                   native_tests=21843, restored_fasls=report['restored_fasls'],
                   admission='Not recounted; prior proposal is 2044 of 2231.',
                   scope='Original EQ/EQL cached method selection, list/lexpr delivery, callable GF dcode and rebinding. Method tables are constructed by the owner fixture. Class applicability, specificity sorting, ADD-METHOD and cache construction/invalidation remain owed. No LL15 credit.')
    summary['files'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(HERE.iterdir()) if p.is_file()}
    (out / 'method-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
