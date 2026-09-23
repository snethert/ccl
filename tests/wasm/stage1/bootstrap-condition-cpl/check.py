"""Bind this unit's class-based execution and unchanged legacy code."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backend

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())


def check(out, native):
    assert read(native / 'run.json')['status'] == 'PASS'
    assert read(native / 'run.json')['registered_tests']['passed'] == 21843
    unit = out / 'compiled/proposal'
    assert read(unit / 'unit.json') == read(native / 'proposal/unit.json')
    assert (unit / 'files' / backend.BACKEND).read_text() == backend.generate()
    assert (out / 'driver/compile.lisp').read_bytes() == (out / 'compiled/source/compile.lisp').read_bytes()
    rows = read(out / 'compiled/native.json')
    new = [r for r in rows if r['definition'].startswith('CORE-CPL-')]
    names = {'CORE-CPL-' + n for n in ('SELECT', 'DECLINE', 'TYPES', 'RESTART', 'CONSTRUCT', 'RESIGNAL')}
    assert {r['definition'] for r in new} == names and len(new) == 24
    execution = read(out / 'execution.json')
    assert execution['status'] == 'PASS'
    comparisons = sum(row['comparisons'] for row in execution['rows'])
    assert comparisons == 25772 + 4 * len(new), comparisons
    parent = backend.ROOT.parent / 'ccl-evidence/2026-09-22-stage1-lap-acceptance'
    baseline = read(parent / 'artifacts.json')
    identical = []
    for name, digest in baseline.items():
        if name.startswith('baseline/compiled/') and name.endswith('.wasm'):
            target = out / name.removeprefix('baseline/')
            assert target.is_file() and sha(target) == digest, name
            identical.append(name)
    assert len(identical) > 2900
    catalog = read(out / 'catalog/results.json')
    assert all(r['checks'] == 16 and len(r['rejected']) == 4 for r in catalog['reports'])
    assert read(out / 'owner-check/results.json')['checks'] == 40
    summary = dict(status='PASS', original_definition_headline=550,
        original_non_nil_headline=515, original_execution_gain=0,
        admission_recounted=False, new_protocol_callers=len(names),
        native_cases=len(new), cpl_comparisons=4 * len(new), comparisons=comparisons,
        legacy_binaries_identical=len(identical),
        catalog_checks=32, catalog_faults=4, native_tests=21843,
        compiler_sha256=sha(unit / 'files' / backend.BACKEND),
        class_typep_source='level-1/l1-typesys.lisp',
        scope='Opt-in class/CPL handler matching. Existing constructors/readers retain their admitted schemas; no complete condition-system or image/READY claim.')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())))
