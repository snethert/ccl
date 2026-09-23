"""Check execution credit and bind the method-dispatch proposal's results."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT.parent / 'ccl-evidence/2026-09-22-stage1-method-dispatch-r1'
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
    required = {r['definition'] for r in rows if r['definition'].startswith('CORE-GENERIC-')}
    assert required == {'CORE-GENERIC-' + name for name in (
        'ORDER', 'APPLICABLE', 'CALL', 'STANDARD', 'SELECT', 'UPDATES', 'FAILURE',
        'RESUME', 'CREATE', 'REPLACE', 'BUILTIN', 'ARGUMENTS', 'EMPTY-CYCLE', 'READER-DISPATCH')}
    counts = {name: sum(r['definition'] == name for r in rows) for name in sorted(required)}
    assert sum(counts.values()) == 53, counts
    whole = read(out / 'compiled/whole-file.json')
    modules = {r['name'] for r in read(out / 'compiled/modules.json')}
    source_proof = [r for r in whole if r.get('module') in modules and r['name'] in {
        '%COMPUTE-APPLICABLE-METHODS*', 'SORT-METHODS', 'COMPUTE-METHOD-LIST',
        '%%CNM-WITH-ARGS-COMBINED-METHOD-DCODE', '%CALL-NEXT-METHOD-WITH-ARGS',
        '%%BEFORE-AND-AFTER-COMBINED-METHOD-DCODE', '%%CHECK-KEYWORDS',
        '%%ASSQ-COMBINED-METHOD-DCODE', '%%ASSOC-COMBINED-METHOD-DCODE'}]
    assert len({r['name'] for r in source_proof}) == 9, source_proof
    census = read(out / 'census.json')
    assert census == dict(standard_generic_functions=581, methods=1514,
                         uninitialized_prototypes=1, other_combinations=0)
    populations = read(out / 'population-checks.json')
    assert populations['status'] == 'PASS' and populations['checks'] == 28
    workers = read(out / 'execution.json')['rows']
    comparisons = sum(r['comparisons'] for r in workers)
    assert comparisons == 4 * len(rows)
    report = read(native / 'run.json')
    assert report['status'] == 'PASS' and report['registered_tests']['passed'] == 21843
    for name, text in {backend.previous.parent.BACKEND: backend.generate(), backend.previous.parent.ARCH: backend.arch(),
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
                   scope='Uncached standard generic dispatch required by the pinned bootstrap census, with original CCL applicability, ordering, combination and method lifecycle. Native-image class/method graphs; target-side GF construction. Custom method combinations and construction of the full cross-dumped CLOS image are not qualified. No LL15 credit.')
    summary['bootstrap_census'] = census
    summary['population_checks'] = populations['checks']
    owner = read(out / 'owner-check/results.json')
    assert owner['status'] == 'PASS' and owner['checks'] == 40
    summary['owner_checks'] = owner['checks']
    summary['metadata_checks'] = sum(len(r['keywordMetadata']) for r in workers)
    for name, text in backend.runtime_files().items():
        assert (out / 'runtime' / name).read_text() == text, name
    controls = read(out / 'generic-controls.json')
    assert controls['status'] == 'PASS' and controls['rejected'] == 8
    summary['rejected_controls'] = controls['rejected']
    summary['files'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(HERE.iterdir()) if p.is_file()}
    (out / 'generic-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
