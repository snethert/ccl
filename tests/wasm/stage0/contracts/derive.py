"""Derive the wasm32 layout schema rows from the pinned U1 x8632 sources.

A small reader for the subset of Common Lisp used by compiler/X86/X8632/
x8632-arch.lisp at U1: defconstant, ccl::defenum, define-subtag and its two
wrappers, define-storage-layout, define-lisp-object, define-fixedsized-object
and define-header, with integer arithmetic over previously defined constants.
Reader conditionals honour the x8632 non-Windows feature set. Every other
top-level form is read and ignored. The C header lisp-kernel/x86-constants32.h
is parsed for the same names so both sides can be compared.
"""
import re
from pathlib import Path

FEATURES = {'x8632-target', 'x86-target', '32-bit-target', 'little-endian-target', 'darwin-target', 'unix-target'}
WORD = 4


class Sym(str):
    """A Lisp symbol; package prefixes are dropped, case is folded."""


def tokenize(text):
    i, n, out = 0, len(text), []
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == ';':
            while i < n and text[i] != '\n':
                i += 1
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(('string', text[i + 1:j])); i = j + 1
        elif c in '()':
            out.append((c, c)); i += 1
        elif c in "'`":
            out.append(('quote', c)); i += 1
        elif c == ',':
            if text[i + 1] == '@':
                out.append(('quote', ',@')); i += 2
            else:
                out.append(('quote', ',')); i += 1
        elif c == '#':
            d = text[i + 1]
            if d in '+-':
                out.append(('cond', d)); i += 2
            elif d == "'":
                out.append(('quote', "#'")); i += 2
            elif d == '.':
                out.append(('quote', '#.')); i += 2
            elif d == '\\':
                j = i + 2
                while j < n and not text[j].isspace() and text[j] not in '()':
                    j += 1
                if j == i + 2: j += 1
                out.append(('char', text[i + 2:j])); i = j
            elif d in 'xXbBoO':
                j = i + 2
                while j < n and (text[j].isalnum() or text[j] in '+-'):
                    j += 1
                out.append(('radix', text[i + 1:j])); i = j
            else:
                raise ValueError('unsupported reader macro #' + d)
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"' and not (text[j] == ';'):
                j += 1
            out.append(('atom', text[i:j])); i = j
    return out


def atom(value):
    if re.fullmatch(r'[+-]?\d+', value):
        return int(value)
    if re.fullmatch(r'[+-]?\d+\.', value):
        return int(value[:-1])
    name = value.split('::')[-1].split(':')[-1] if not value.startswith(':') else value
    return Sym(name.lower())


def radix(spec):
    base = {'x': 16, 'b': 2, 'o': 8}[spec[0].lower()]
    return int(spec[1:], base)


class Reader:
    def __init__(self, text):
        self.tokens = tokenize(text); self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self):
        tok = self.tokens[self.pos]; self.pos += 1; return tok

    def feature(self, expr):
        if isinstance(expr, Sym):
            return expr in FEATURES
        if isinstance(expr, list) and expr:
            head = expr[0]
            if head == 'and': return all(self.feature(e) for e in expr[1:])
            if head == 'or': return any(self.feature(e) for e in expr[1:])
            if head == 'not': return not self.feature(expr[1])
        raise ValueError('unsupported feature expression ' + repr(expr))

    def read(self):
        """Read one datum; returns (present, value). Absent means skipped by a conditional."""
        tok = self.next()
        kind, value = tok
        if kind == '(':
            items = []
            while True:
                if self.peek()[0] == ')':
                    self.next(); return True, items
                present, item = self.read()
                if present:
                    if item == Sym('.') and isinstance(item, Sym):
                        present, tail = self.read(); self.next(); return True, items + [Sym('.'), tail]
                    items.append(item)
        if kind == ')':
            raise ValueError('unbalanced )')
        if kind == 'quote':
            present, item = self.read()
            return present, [Sym(value), item]
        if kind == 'cond':
            present, expr = self.read()
            keep = self.feature(expr) if value == '+' else not self.feature(expr)
            present, form = self.read()
            return (keep and present), form
        if kind == 'string': return True, ('string', value)
        if kind == 'char': return True, ('char', value)
        if kind == 'radix': return True, radix(value)
        return True, atom(value)

    def forms(self):
        while self.peek() is not None:
            present, form = self.read()
            if present:
                yield form


class Evaluator:
    def __init__(self):
        self.values = {}; self.order = []

    def define(self, name, value, kind, **extra):
        name = str(name)
        if name in self.values and self.values[name] != value:
            raise ValueError('redefinition of ' + name)
        self.values[name] = value
        self.order.append(dict(name=name, value=value, kind=kind, **extra))

    def ev(self, expr):
        if isinstance(expr, bool) or expr is None:
            raise ValueError('unsupported literal')
        if isinstance(expr, int):
            return expr
        if isinstance(expr, Sym):
            if expr not in self.values:
                raise ValueError('undefined constant ' + expr)
            return self.values[expr]
        if isinstance(expr, list) and expr:
            head, args = expr[0], expr[1:]
            ops = {'+': lambda a: sum(a), '*': lambda a: __import__('math').prod(a),
                   'logior': lambda a: __import__('functools').reduce(lambda x, y: x | y, a, 0),
                   'logand': lambda a: __import__('functools').reduce(lambda x, y: x & y, a, -1)}
            if head in ops:
                return ops[head]([self.ev(a) for a in args])
            if head == '-':
                vals = [self.ev(a) for a in args]
                return -vals[0] if len(vals) == 1 else vals[0] - sum(vals[1:])
            if head == 'ash':
                a, b = self.ev(args[0]), self.ev(args[1])
                return a << b if b >= 0 else a >> -b
            if head == '1-': return self.ev(args[0]) - 1
            if head == '1+': return self.ev(args[0]) + 1
            if head == 'byte': return ('byte', self.ev(args[0]), self.ev(args[1]))
        raise ValueError('unsupported expression ' + repr(expr))


def derive(lisp_text):
    """Return the ordered row table derived from the Lisp source."""
    ev = Evaluator()
    subtags, objects, layouts, headers, enums = [], [], [], [], []

    def define_storage_layout(name, origin, cells):
        base = ev.ev(origin)
        rows = []
        for index, cell in enumerate(cells):
            cell_name = str(name) + '.' + str(cell)
            ev.define(cell_name, base + index * WORD, 'layout-cell', layout=str(name), cell=str(cell), index=index)
            rows.append(dict(cell=str(cell), index=index, offset=base + index * WORD))
        ev.define(str(name) + '.size', len(cells) * WORD, 'layout-size', layout=str(name))
        return dict(name=str(name), origin=base, size=len(cells) * WORD, cells=rows)

    def handle(form):
        if not isinstance(form, list) or not form:
            return
        head = form[0]
        if head in ('eval-when', 'progn'):
            for sub in form[1:] if head == 'progn' else form[2:]:
                handle(sub)
        elif head == 'defconstant':
            ev.define(form[1], ev.ev(form[2]), 'constant')
        elif head == 'defenum':
            options = form[1] if isinstance(form[1], list) else []
            opts = {str(options[i]): options[i + 1] for i in range(0, len(options), 2)}
            prefix = opts.get(':prefix', ('string', ''))[1]; suffix = opts.get(':suffix', ('string', ''))[1]
            start = ev.ev(opts.get(':start', 0)); step = ev.ev(opts.get(':step', 1))
            names = []
            for index, ident in enumerate(form[2:]):
                ident = ident[0] if isinstance(ident, list) else ident
                name = (prefix + str(ident) + suffix).lower()
                ev.define(name, start + index * step, 'enum', enum=prefix or 'registers')
                names.append(dict(name=name, value=start + index * step))
            enums.append(dict(prefix=prefix, start=start, step=step, names=names))
        elif head in ('define-subtag', 'define-imm-subtag', 'define-node-subtag'):
            if head == 'define-subtag':
                name, tag_expr, index = form[1], form[2], form[3]
            else:
                name, index = form[1], form[2]
                tag_expr = Sym('fulltag-immheader' if head == 'define-imm-subtag' else 'fulltag-nodeheader')
            tag = ev.ev(tag_expr); index = ev.ev(index)
            value = tag | (index << ev.values['ntagbits'])
            ev.define('subtag-' + str(name), value, 'subtag', tag=str(tag_expr), index=index)
            subtags.append(dict(name='subtag-' + str(name), tag=str(tag_expr), tag_value=tag, index=index, value=value))
        elif head == 'define-storage-layout':
            layouts.append(define_storage_layout(form[1], form[2], form[3:]))
        elif head == 'define-lisp-object':
            tag = ev.ev(form[2]); layout = define_storage_layout(form[1], -tag, form[3:])
            objects.append(dict(name=str(form[1]), tag=str(form[2]), tag_value=tag, header=str(form[3]) == 'header', layout=layout))
        elif head == 'define-fixedsized-object':
            tag = ev.ev(Sym('fulltag-misc')); cells = [Sym('header')] + form[2:]
            layout = define_storage_layout(form[1], -tag, cells)
            for index, cell in enumerate(form[2:]):
                ev.define(str(form[1]) + '.' + str(cell) + '-cell', index, 'cell-index', object=str(form[1]))
            ev.define(str(form[1]) + '.element-count', len(form[2:]), 'element-count', object=str(form[1]))
            objects.append(dict(name=str(form[1]), tag='fulltag-misc', tag_value=tag, header=True, layout=layout, element_count=len(form[2:])))
        elif head == 'define-header':
            value = (ev.ev(form[2]) << ev.values['num-subtag-bits']) | ev.ev(form[3])
            ev.define(form[1], value, 'header', element_count=ev.ev(form[2]), subtag=str(form[3]))
            headers.append(dict(name=str(form[1]), element_count=ev.ev(form[2]), subtag=str(form[3]), value=value))
        elif head == 'let*':
            pass  # the subprimitive table; extracted textually below
    for form in Reader(lisp_text).forms():
        handle(form)
    subprims = re.findall(r'\(defx8632subprim\s+([^\s()]+)\)', lisp_text)
    base = ev.values['x8632-subprims-base']; shift = 2
    subprim_rows = [dict(name=n, index=i, address=base + (i << shift)) for i, n in enumerate(subprims)]
    return dict(values=ev.values, order=ev.order, subtags=subtags, objects=objects, layouts=layouts, headers=headers, enums=enums, subprims=subprim_rows)


def c_constants(header_text):
    """Evaluate the tag, subtag, NIL/T and offset #defines of x86-constants32.h."""
    env = {'LOWMEM_BIAS': 0}
    macros = {}
    for line in header_text.splitlines():
        m = re.match(r'#define\s+(\w+)\(([^)]*)\)\s+(.*)', line)
        if m:
            macros[m.group(1)] = ([a.strip() for a in m.group(2).split(',')], m.group(3).strip()); continue
        m = re.match(r'#define\s+(\w+)\s+(.+?)\s*(/\*.*)?$', line)
        if not m:
            continue
        name, expr = m.group(1), m.group(2).strip()
        if name.startswith('TCR_BIAS'):
            continue
        try:
            env[name] = c_eval(expr, env, macros)
        except (KeyError, ValueError, SyntaxError, NameError, TypeError):
            pass
    return env


def c_eval(expr, env, macros):
    expr = re.sub(r'\s+', ' ', expr)
    changed = True
    while changed:
        changed = False
        for name, (params, body) in macros.items():
            pattern = re.compile(r'\b' + name + r'\(([^()]*)\)')
            m = pattern.search(expr)
            if m:
                args = [a.strip() for a in m.group(1).split(',')]
                if len(args) != len(params):
                    raise ValueError('macro arity')
                replacement = body
                for p, a in zip(params, args):
                    replacement = re.sub(r'\b' + re.escape(p) + r'\b', '(' + a + ')', replacement)
                expr = expr[:m.start()] + '(' + replacement + ')' + expr[m.end():]; changed = True
    tokens = re.findall(r'\w+|<<|>>|[-+*/|&()~]', expr)
    if not tokens or ''.join(tokens).replace(' ', '') != expr.replace(' ', ''):
        raise ValueError('unsupported C expression ' + expr)
    py = ' '.join(str(env[t]) if re.fullmatch(r'[A-Za-z_]\w*', t) else t for t in tokens)
    return int(eval(py, {'__builtins__': {}}, {}))


if __name__ == '__main__':
    import json, sys
    root = Path(__file__).resolve().parents[4]
    table = derive((root / 'compiler/X86/X8632/x8632-arch.lisp').read_text())
    print(json.dumps(dict(constants=[r for r in table['order'] if r['kind'] == 'constant'], subtags=len(table['subtags']), objects=[o['name'] for o in table['objects']],
                          layouts=[(l['name'], len(l['cells'])) for l in table['layouts']], headers=len(table['headers']), enums=[(e['prefix'], len(e['names'])) for e in table['enums']],
                          subprims=len(table['subprims'])), indent=1)[:6000])
