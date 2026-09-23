"""Check native execution and final-source qualification, without slot credit."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backend

read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def check(out, native):
    qualification = read(native / 'run.json')
    assert qualification['status'] == 'PASS'
    assert qualification['registered_tests']['passed'] == 21843
    assert qualification['restored_fasls'] == 164
    unit = out / 'compiled/proposal'
    assert read(unit / 'unit.json') == read(native / 'proposal/unit.json')
    manifest = read(unit / 'unit.json')
    for row in manifest['added'] + manifest['modified']:
        name = row['path']
        assert sha(unit / 'files' / name) == sha(native / 'proposal/files' / name), name
    assert (unit / 'files' / backend.BACKEND).read_text() == backend.generate()
    assert (out / 'driver/compile.lisp').read_bytes() == (out / 'compiled/source/compile.lisp').read_bytes()
    for source, copy in [('methods.lisp', 'driver/condition-methods.lisp'),
                         ('inputs.lisp', 'driver/cpl-inputs.lisp'),
                         ('graph.lisp', 'driver/graph.lisp'),
                         ('check.mjs', 'check.mjs'), ('install.mjs', 'install.mjs'),
                         ('graph.mjs', 'graph.mjs')]:
        assert (HERE / source).read_bytes() == (out / copy).read_bytes(), source
    assert (out / 'driver/numeric-files.lisp').read_text().endswith((HERE / 'class-typep.lisp').read_text())
    rows = read(out / 'compiled/native.json')
    callers = set(read(out / 'compiled/condition-callers.json'))
    new = [r for r in rows if r['definition'] in callers]
    assert len(callers) == 24 and len(new) == 45
    parent = backend.ROOT.parent / 'ccl-evidence/2026-09-23-stage1-class-table-r1'
    with tarfile.open(parent / 'execution.tar.gz') as archive:
        old = json.load(archive.extractfile('compiled/native.json'))
    before, after = Counter(r['definition'] for r in old), Counter(r['definition'] for r in rows)
    assert not before - after, before - after
    assert after - before == Counter({
        'CORE-CONDITION-TABLE-GROW': 2, 'CORE-CONDITION-TABLE-REMOVE': 1,
        'CORE-CONDITION-REMOVE-READ-ONLY': 1, 'CORE-CONDITION-OWN-TABLE': 1,
        'CORE-CONDITION-TABLE-CLEAR': 1, 'CORE-CONDITION-IMPLICIT-TYPE': 4,
        'CORE-CONDITION-IMPLICIT-DIVIDE': 3, 'CORE-CONDITION-IMPLICIT-UNBOUND': 1,
        'CORE-CONDITION-IMPLICIT-UNDEFINED': 1, 'CORE-CONDITION-IMPLICIT-FLOAT': 1})

    execution = read(out / 'execution.json')
    assert execution['status'] == 'PASS'
    comparisons = sum(r['comparisons'] for r in execution['rows'])
    assert comparisons == 4 * len(rows) == 26048, comparisons
    assert all(not r.get('focused') for r in execution['rows'])
    modules = read(out / 'compiled/modules.json')
    assert any(m['cplMode'] for m in modules)
    assert any(not m['cplMode'] for m in modules)
    assert 'condition_class_cells' not in (out / 'install.mjs').read_text()
    class_modules = [m for m in modules if m['cplMode'] or
                     m['name'].startswith('core_condition_implicit_')]
    for module in class_modules:
        wat = (out / 'compiled' / (module['name']+'.wat')).read_text()
        assert 'condition_registry' not in wat, module['name']
        assert '(func $condition_new' not in wat, module['name']
        assert '(func $condition_mask' not in wat, module['name']
    assert (out / 'compiled/eq-initializer-refusal.sexp').read_text().strip() == ':EQ-VECTOR-INITIAL-ELEMENT'
    for row in execution['rows']:
        assert len(row['growthChecks']) == 15, row['growthChecks']

    class_counts = {len(node['hash']) for r in new for node in r['args'][0]['graph']['nodes'] if 'hash' in node}
    assert len(class_counts) == 1 and next(iter(class_counts)) > 500
    assert read(out / 'owner-check/results.json')['checks'] == 40
    summary = dict(status='PASS', original_definition_headline=550,
        original_non_nil_headline=515, original_execution_gain=0,
        admission_recounted=False, condition_callers=len(callers),
        condition_cases=len(new), new_comparisons=4*(len(rows)-len(old)),
        inherited_cases=len(old), total_native_cases=len(rows), comparisons=comparisons,
        class_cells=next(iter(class_counts)), modules=len(modules),
        class_mode_modules=sum(m['cplMode'] for m in modules),
        collections=sum(r['collections']+r['internalCollections'] for r in execution['rows']),
        collector_owner_checks=40, native_tests=21843,
        compiler_sha256=sha(unit / 'files' / backend.BACKEND),
        class_modules_without_registry=len(class_modules), growth_checks=sum(len(r['growthChecks']) for r in execution['rows']),
        scope='Default-off target-owned class table, growth to 16384 entries, REMHASH, CLRHASH and class-based implicit failure construction. Class-mode modules emit no condition registry. Class objects remain native-projected; cross-dumped image/READY and removal of the legacy mode remain open.')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())))
