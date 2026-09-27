"""Enumerate Wasm reader branches without treating them as original-body credit.

This is a lexical inventory, not a Common Lisp macroexpander. CCL's reader
matrix and native FASL comparisons separately establish native equivalence.
"""
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[4]
DEFINITION = re.compile(r'^(DEFUN|DEFMETHOD|DEFMACRO|DEFGENERIC|DEF.*LAPFUNCTION|DEFINE-COMPILER-MACRO)$')


def read_nodes(text):
    pos = 0
    def space():
        nonlocal pos
        while pos < len(text):
            if text[pos].isspace(): pos += 1
            elif text[pos] == ';':
                end = text.find('\n', pos); pos = len(text) if end < 0 else end
            elif text.startswith('#|', pos):
                pos += 2; depth = 1
                while depth:
                    assert pos < len(text), 'unterminated block comment'
                    if text.startswith('#|', pos): depth += 1; pos += 2
                    elif text.startswith('|#', pos): depth -= 1; pos += 2
                    else: pos += 1
            else: break
    def node():
        nonlocal pos
        space(); start = pos
        if text.startswith(('#+', '#-'), pos):
            kind = text[pos:pos+2]; pos += 2
            children = [node(), node()]
        elif text.startswith("#'", pos) or text.startswith('#.', pos):
            kind = text[pos:pos+2]; pos += 2; children = [node()]
        elif text[pos] in "'`,":
            kind = text[pos]; pos += 1
            if kind == ',' and text[pos:pos+1] in ('@', '.'): kind += text[pos]; pos += 1
            children = [node()]
        elif text[pos] == '(' or text.startswith('#(', pos):
            kind = 'list' if text[pos] == '(' else 'vector'; pos += 1 if kind == 'list' else 2
            children = []
            while True:
                space(); assert pos < len(text), 'unterminated list'
                if text[pos] == ')': pos += 1; break
                children.append(node())
        else:
            kind = 'atom'; children = []
            if text.startswith('#\\', pos):
                pos += 2; assert pos < len(text); pos += 1
                while pos < len(text) and not text[pos].isspace() and text[pos] not in '()': pos += 1
            else:
                quoted = None
                while pos < len(text):
                    ch = text[pos]
                    if ch == '\\': pos += 2; continue
                    if quoted:
                        pos += 1
                        if ch == quoted: quoted = None
                    elif ch in ('"', '|'): quoted = ch; pos += 1
                    elif ch.isspace() or ch in '();': break
                    else: pos += 1
                assert quoted is None, 'unterminated quoted token'
            assert pos > start, ('unexpected token', start)
        return dict(kind=kind, start=start, end=pos, children=children)
    result = []
    while True:
        space()
        if pos == len(text): return result
        result.append(node())


def inventory():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'ready'))
    from replacements import upstream_definitions, ROUTES
    native = upstream_definitions()
    paths = subprocess.check_output(['rg', '--files', 'level-0', 'level-1', 'lib', 'library', 'compiler'],
                                    cwd=ROOT, text=True).splitlines()
    rows = []; sources = {}; definitions = {}; primitives = []
    for name in sorted(paths):
        if not name.endswith(('.lisp', '.lap')): continue
        target = '/WASM32/' in name
        if target and name.startswith('compiler/'): continue
        text = (ROOT/name).read_text()
        if not target and 'wasm32-target' not in text.lower(): continue
        sources[name] = hashlib.sha256(text.encode()).hexdigest()
        def value(n): return text[n['start']:n['end']]
        def head(n):
            return value(n['children'][0]).upper() if n['kind']=='list' and n['children'] else None
        def definition(n):
            h = head(n)
            if h and DEFINITION.fullmatch(h) and len(n['children']) > 1:
                return dict(kind=h, name=value(n['children'][1]).upper(),
                            line=text.count('\n', 0, n['start'])+1, start=n['start'])
        def feature(n, assignment):
            if n['kind']=='atom': return assignment[value(n).upper()]
            h=head(n); args=n['children'][1:]
            if h=='NOT': assert len(args)==1; return not feature(args[0], assignment)
            assert h in ('AND','OR'), value(n)
            return (all if h=='AND' else any)(feature(a,assignment) for a in args)
        def atoms(n):
            if n['kind']=='atom': return {value(n).upper()}
            return set().union(*(atoms(c) for c in n['children'][1:]))
        def visit(n, enclosing=None):
            named = definition(n)
            current = named or enclosing
            if named and target:
                symbol = named['name'].split('::')[-1]
                antecedent = ROUTES.get(symbol, symbol)
                primitives.append(dict(source=name, **named, native_name=antecedent,
                    native_candidates=native.get(antecedent, []), original_execution_credit=False))
            if n['kind'] in ('#+', '#-') and 'WASM32-TARGET' in atoms(n['children'][0]):
                f, body = n['children']; others = sorted(atoms(f)-{'WASM32-TARGET'})
                outcomes = {}
                for wasm in (False, True):
                    outcomes[wasm] = sorted(set(feature(f, dict(zip(others, values), **{'WASM32-TARGET': wasm})) == (n['kind']=='#+')
                                                for values in itertools.product((False,True), repeat=len(others))))
                d = definition(body)
                classification = ('BODY_BRANCH' if enclosing else
                                  'EXCLUDED_FORM' if outcomes[True]==[False] else
                                  'WASM_ONLY_DEFINITION' if d and outcomes[False]==[False] else
                                  'TOPLEVEL_BRANCH')
                row = dict(source=name, line=text.count('\n',0,n['start'])+1,
                           classification=classification, conditional=n['kind'], feature=value(f),
                           wasm_outcomes=outcomes[True], other_target_outcomes=outcomes[False],
                           governed_head=head(body), definition=d, enclosing_definition=enclosing,
                           form_sha256=hashlib.sha256(value(body).encode()).hexdigest())
                if not target: rows.append(row)
                if enclosing: definitions[(name,enclosing['start'])] = dict(source=name, **enclosing)
            for child in n['children']: visit(child,current)
        for n in read_nodes(text): visit(n)
    return dict(version=1, status='ENUMERATED', replacement_cap=None,
                counts=dict(Counter(r['classification'] for r in rows)),
                definitions_with_body_branches=len(definitions),
                body_definitions=list(definitions.values()), sources=sources, sites=rows,
                target_primitive_definitions=primitives,
                scope='All source-tree shared Lisp and LAP files under level-0, level-1, lib, library and compiler, plus every named level-0/level-1 Wasm primitive definition. Includes branches in files outside the READY load closure. Native name matches are candidate antecedents, not original-body execution credit.',
                limitations='Counts are reader-conditional sites and unique enclosing named definitions, not semantic replacement or execution counts. Unknown non-Wasm features are varied over all assignments; no native target is inferred from one feature set. Macro-generated definitions and backend routes require the separate compiler/runtime inventory. Every body branch is enumerated regardless of whether it replaces foreign, assembly or portable Lisp code.')


if __name__=='__main__':
    result=inventory(); Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','counts','definitions_with_body_branches')}))
