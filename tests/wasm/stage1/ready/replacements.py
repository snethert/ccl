"""Inventory every reached callable by name; missing provenance is not exemption."""
from pathlib import Path
from collections import Counter, defaultdict
import re
import subprocess
from closure import read, digest

ROOT = Path(__file__).resolve().parents[4]
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
ROUTES = {
    '%WASM-ERROR': 'ERROR', '%WASM-KERNEL-RESTART': '%KERNEL-RESTART',
    '%WASM-CLASS-GETHASH': 'GETHASH', '%WASM-CLASS-PUTHASH': 'PUTHASH',
    '%WASM-CLASS-REMHASH': 'REMHASH', '%WASM-CLASS-CLRHASH': 'CLRHASH',
    '%WASM-EQL-SPECIALIZER-READER': 'EQL-SPECIALIZER-OBJECT',
    'CORE-GENERIC-CLASS-OF-FUNCTION': 'CLASS-OF',
    'CORE-GENERIC-CLASS-OF-INSTANCE': 'CLASS-OF',
    'CORE-GENERIC-CLASS-OF-LIST': 'CLASS-OF',
}


def upstream_definitions():
    # Search the full upstream source, including compiler/optimizers.lisp.
    # x8632 LAP definitions are contracts even where x8664 uses a DEFUN.
    kinds = r'defun|defmethod|defmacro|define-compiler-macro|def[a-z0-9]*lapfunction'
    text = subprocess.check_output(['git', 'grep', '-n', '-i', '-E',
        r'^[[:space:]]*\((' + kinds + r')[[:space:]]', U1, '--', '*.lisp', '*.lap'],
        cwd=ROOT, text=True)
    native = defaultdict(list)
    for line in text.splitlines():
        revision, path, number, body = line.split(':', 3)
        match = re.search(r'\((' + kinds + r')\s+(\(setf\s+[^)]+\)|[^\s()]+)', body, re.I)
        if not match:
            continue
        name = re.sub(r'\s+', ' ', match[2]).upper()
        # This is an antecedent index, not a claim of compiled form equality.
        native[name].append(dict(kind=match[1].upper(), source=path,
                                 line=int(number), text=body.strip()))
    return native


def census(closure):
    native = upstream_definitions()
    rows = []
    for m in closure['modules']:
        name = m['name'].split('::', 1)[-1] if m['name'] else None
        previous = native.get(ROUTES.get(name, name), [])
        target = 'WASM32;' in m['source'] or (m['name'] or '').startswith('WASM32-COMPILER::')
        if not name:
            kind = 'ANONYMOUS_CODE'
        elif name in ROUTES:
            kind = 'RENAMED_REPLACEMENT'
        elif target and any('LAPFUNCTION' in row['kind'] for row in previous):
            kind = 'NATIVE_LAP_ANTECEDENT'
        elif target and previous:
            kind = 'TARGET_WITH_NATIVE_ANTECEDENT'
        elif target:
            kind = 'TARGET_REQUIRING_ATTRIBUTION'
        elif previous:
            kind = 'NATIVE_NAME_ANTECEDENT'
        else:
            kind = 'NAME_REQUIRING_ATTRIBUTION'
        source = m['source']
        path = ROOT / (source[4:].replace(';', '/') if source.startswith('ccl:') else source)
        rows.append(dict(name=m['name'], module=m['module'], source=source,
                         source_sha256=digest(path) if source and path.is_file() else None,
                         classification=kind, native=previous, replaces=ROUTES.get(name),
                         attribution_complete=False if kind in (
                             'TARGET_REQUIRING_ATTRIBUTION', 'NAME_REQUIRING_ATTRIBUTION') else None))
    assert {r['module'] for r in rows} == {m['module'] for m in closure['modules']}
    assert len(rows) == len(closure['modules'])
    counts = Counter(row['classification'] for row in rows)
    return dict(version=2, upstream=U1, cap=25, entries=rows,
                reached_modules=len(rows), named_modules=sum(r['name'] is not None for r in rows),
                source_unattributed=sum(not r['source'] for r in rows),
                counts=dict(sorted(counts.items())), enumeration_complete=True,
                complete=False, cap_satisfied=None,
                limitation='Every reached module is listed, including anonymous code and source-less '
                           'CORE/scan entries. Native name matches identify candidate antecedents, not '
                           'unchanged bodies. Extracted methods, generated accessors, source branches '
                           'and backend substitutions still require form/route attribution before '
                           'the high-level replacement cap can be decided.')


def controls(closure):
    from copy import deepcopy
    actual = census(closure)
    stripped = deepcopy(closure)
    for m in stripped['modules']:
        m['source'] = ''
    probe = census(stripped)
    assert [(r['module'], r['name']) for r in actual['entries']] == [
        (r['module'], r['name']) for r in probe['entries']]
    core = [m for m in closure['modules'] if (m['name'] or '').startswith('WASM32-COMPILER::CORE-')]
    assert core and all(any(r['module']==m['module'] for r in actual['entries']) for m in core)
    native = upstream_definitions()
    assert any(r['source']=='compiler/optimizers.lisp' for r in native['ASSQ'])
    assert any(r['kind']=='DEFX8632LAPFUNCTION' for r in native['%BIGNUM-REF'])
    return dict(status='PASS', checks=['blank source cannot remove reached modules',
        'CORE helpers cannot escape enumeration', 'ASSQ compiler antecedent',
        'x8632 LAP antecedent'], reached_modules=len(actual['entries']))


if __name__ == '__main__':
    import json, sys
    Path(sys.argv[2]).write_text(json.dumps(census(read(Path(sys.argv[1]))), indent=2) + '\n')
