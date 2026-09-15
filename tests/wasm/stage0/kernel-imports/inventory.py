"""Derive the kernel-import inventory from the pinned U1 sources.

The C table is lisp-kernel/imports.s (defimport order); the Lisp table is the
KERNEL-IMPORT- enumeration in compiler/X86/X8632/x8632-arch.lisp. They are
joined by index. Lisp callers are found by scanning the U1 Lisp sources for
the kernel-import-<name> constants; C and assembly definitions and C call
sites are found in lisp-kernel.
"""
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('contracts_derive', HERE.parent / 'contracts' / 'derive.py')
_module = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_module)
derive_arch = _module.derive

LISP_DIRS = ['level-0', 'level-1', 'lib', 'library', 'compiler']
ARCH_FILES = {'x8632-arch.lisp', 'x8664-arch.lisp', 'arm-arch.lisp', 'ppc32-arch.lisp', 'ppc64-arch.lisp'}
OTHER_TARGET = re.compile(r'(^|/)(PPC|ARM|X8664)(/|$)|(^|/)(ppc|arm)-[^/]*\.lisp$|x86-utils\.lisp$|x8664')


def c_table(text):
    return re.findall(r'defimport\((\w+)\)', text)


def lisp_table(text):
    table = derive_arch(text)
    enum = next(e for e in table['enums'] if e['prefix'].lower() == 'kernel-import-')
    return [dict(name=n['name'][len('kernel-import-'):], offset=n['value']) for n in enum['names']]


ALIASES = {'cooperative-thread-startup': 'do_nothing', 'put-altivec-registers': 'put_vector_registers', 'get-altivec-registers': 'get_vector_registers'}


def names_agree(lisp_name, c_name):
    """The Lisp spelling names the same entry as the C spelling at the same index."""
    if ALIASES.get(lisp_name) == c_name:
        return True
    l = lisp_name.lower().replace('-', '_'); c = c_name.lower()
    for prefix in ('lisp_', 'x'):
        if c.startswith(prefix) and not l.startswith(prefix):
            c = c[len(prefix):]
    return l == c


def join(c_names, lisp_entries):
    if len(c_names) != len(lisp_entries):
        raise ValueError('TABLE count C %d versus Lisp %d' % (len(c_names), len(lisp_entries)))
    rows = []
    for index, (c, l) in enumerate(zip(c_names, lisp_entries)):
        if l['offset'] != index * 4:
            raise ValueError('TABLE offset ' + l['name'])
        if not names_agree(l['name'], c):
            raise ValueError('TABLE name ' + l['name'] + ' versus ' + c + ' at index %d' % index)
        rows.append(dict(index=index, offset=l['offset'], lisp_name=l['name'], c_name=c))
    return rows


def classify_form(line):
    stripped = line.strip()
    if stripped.startswith(';'):
        return 'comment'
    if 'int-errno-ffcall' in line:
        return 'int-errno-ffcall'
    if 'ff-call' in line:
        return 'ff-call'
    if '%kernel-import' in line:
        return '%kernel-import'
    return 'other'


def lisp_callers(root, rows):
    """Every source line naming a kernel-import constant, with its form and target applicability."""
    pattern = re.compile(r'kernel-import-([A-Za-z0-9-]+)', re.IGNORECASE)
    by_name = {r['lisp_name'].lower(): r['lisp_name'] for r in rows}
    callers = {r['lisp_name']: [] for r in rows}
    for d in LISP_DIRS:
        for path in sorted((root / d).rglob('*.lisp')):
            if path.name in ARCH_FILES:
                continue
            rel = path.relative_to(root).as_posix()
            for ln, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
                for m in pattern.finditer(line):
                    name = by_name.get(m.group(1).lower())
                    if not name:
                        continue
                    form = classify_form(line)
                    callers[name].append(dict(file=rel, line=ln, form=form, x8632=not OTHER_TARGET.search(rel) and form != 'comment'))
    return callers


def c_definitions(root, rows):
    """Definition sites in lisp-kernel C and assembly, and C call-site counts."""
    definitions = {r['c_name']: [] for r in rows}; calls = {r['c_name']: 0 for r in rows}
    kernel = root / 'lisp-kernel'
    for path in sorted(list(kernel.glob('*.c')) + list(kernel.glob('*.h')) + list(kernel.glob('*.s'))):
        if path.name == 'imports.s':
            continue
        for ln, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            for r in rows:
                n = r['c_name']
                if n not in line:
                    continue
                if path.suffix == '.s':
                    if re.search(r'_exportfn\(C\(' + re.escape(n) + r'\)\)', line):
                        definitions[n].append(path.name + ':' + str(ln))
                    continue
                stripped = line.strip()
                if re.match(r'^(?:[\w\* ]+\s+)?\*?' + re.escape(n) + r'\s*\(', line) and not stripped.startswith(('extern', '//', '/*')) and not stripped.endswith(';'):
                    definitions[n].append(path.name + ':' + str(ln))
                elif re.search(r'\b' + re.escape(n) + r'\s*\(', line) and not stripped.startswith(('extern', '//', '/*', '#')):
                    calls[n] += 1
    return definitions, calls
