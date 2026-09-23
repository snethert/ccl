"""Name target definitions and their native antecedents without hiding helpers."""
from pathlib import Path
from collections import Counter, defaultdict
import json
import re
import subprocess
from closure import read, digest

ROOT = Path(__file__).resolve().parents[4]
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'

# Renaming a replacement does not exempt it from the cap. These routes are
# explicit in the accepted backend; report alongside same-name definitions.
ROUTES = {
    '%WASM-ERROR': 'ERROR',
    '%WASM-KERNEL-RESTART': '%KERNEL-RESTART',
    '%WASM-CLASS-GETHASH': 'GETHASH',
    '%WASM-CLASS-PUTHASH': 'PUTHASH',
    '%WASM-CLASS-REMHASH': 'REMHASH',
    '%WASM-EQL-SPECIALIZER-READER': 'EQL-SPECIALIZER-OBJECT',
}


def census(closure):
    text = subprocess.check_output(['git', 'grep', '-n', '-i', '-E',
        r'^[[:space:]]*\((defun|defx86lapfunction|defarmlapfunction|defppclapfunction)[[:space:]]',
        U1, '--', 'level-0', 'level-1', 'lib', 'library'], cwd=ROOT, text=True)
    native = defaultdict(list)
    for line in text.splitlines():
        match = re.search(r'\((defun|defx86lapfunction|defarmlapfunction|defppclapfunction)\s+\(?(\S+)', line, re.I)
        if match:
            revision, path, number, body = line.split(':', 3)
            native[match[2].upper()].append(dict(kind=match[1].upper(), source=path,
                                                line=int(number), text=body.strip()))
    rows = []
    for m in closure['modules']:
        if 'WASM32;' not in m['source'] or not m['name']:
            continue
        name = m['name'].split('::')[-1]
        previous = native[name]
        if name in ROUTES:
            kind = 'RENAMED_REPLACEMENT'
        elif any(row['kind'] == 'DEFUN' for row in previous):
            kind = 'NATIVE_LISP_ANTECEDENT'
        elif previous:
            kind = 'NATIVE_LAP_ANTECEDENT'
        else:
            kind = 'NO_DIRECT_DEFINITION_FOUND'
        rows.append(dict(name=m['name'], module=m['module'], source=m['source'],
                         classification=kind, native=previous, replaces=ROUTES.get(name),
                         source_sha256=digest(ROOT / m['source'][4:].replace(';', '/'))))
    counts = Counter(row['classification'] for row in rows)
    return dict(version=1, upstream=U1, cap=25, entries=rows,
                counts=dict(sorted(counts.items())), complete=False, cap_satisfied=None,
                limitation='This source-site census is conservative. Native arch DEFUN wrappers may '
                           'implement LAP contracts; macro-generated originals need explicit attribution. '
                           'Source branches and backend substitutions also require disposition. No renamed '
                           'helper is silently treated as exempt and no cap verdict is claimed yet.')


if __name__ == '__main__':
    import sys
    Path(sys.argv[2]).write_text(json.dumps(census(read(Path(sys.argv[1]))), indent=2) + '\n')
