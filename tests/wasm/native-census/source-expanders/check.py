"""Bound source reconstruction, routing, helper joins and reference equivalence."""
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('reviewed_macro_check', HERE.parent/'target-macros/check.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
require, sym, form, elements = prior.require, prior.sym, prior.form, prior.elements
NATIVE_CONTROLS = {'bypass-if': 'SOURCE_ROUTING', 'host-layout': 'LAYOUT_PROBE',
                   'copy-no-change': 'NO_CHANGE_IDENTITY', 'name-only': 'SHADOW_PRECEDENCE'}


def read(p):
    with gzip.open(p, 'rt') if p.suffix == '.gz' else p.open() as f:
        return json.load(f)


def form_end(text, start):
    """Independent scanner for this pinned subset; no Lisp evaluation."""
    require(text[start] == '(', 'SOURCE_OPEN')
    depth, i, string = 0, start, False
    while i < len(text):
        c = text[i]
        if string:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                string = False
        elif c == '"':
            string = True
        elif c == ';':
            newline = text.find('\n', i)
            require(newline >= 0, 'SOURCE_COMMENT_EOF')
            i = newline
        elif text.startswith('#\\', i):
            i += 2
            require(i < len(text), 'SOURCE_CHARACTER_EOF')
            if text[i].isalnum():
                while i + 1 < len(text) and (text[i+1].isalnum() or text[i+1] in '-_'):
                    i += 1
        elif text.startswith('#|', i):
            nesting = 1
            i += 2
            while i < len(text) and nesting:
                if text.startswith('#|', i):
                    nesting += 1
                    i += 2
                elif text.startswith('|#', i):
                    nesting -= 1
                    i += 2
                else:
                    i += 1
            require(nesting == 0, 'SOURCE_COMMENT_EOF')
            i -= 1
        elif c == '|':
            # Escaped symbols are outside this fixed source corpus.
            raise ValueError('SOURCE_SCANNER_UNSUPPORTED')
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('SOURCE_UNTERMINATED')


def manifest():
    m = read(HERE/'manifest.json')
    pins = read(HERE/'source-inputs.json')
    for path, expected in pins.items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, 'SOURCE_PIN')
    rows = m['expanders']
    require(len(rows) == 47 and len({(r['operator'], r['role']) for r in rows}) == 47, 'MANIFEST_BOUND')
    require(len({(r['source'], r['start']) for r in rows}) == 46, 'SOURCE_ALIAS_BOUND')
    require(Counter(r['role'] for r in rows) == {'macro': 15, 'compiler-macro': 30, 'architecture-dispatch': 2}, 'ROLE_BOUND')
    for r in rows:
        text = (ROOT/r['source']).read_text()
        require(r['source_sha256'] == pins[r['source']], 'MANIFEST_SOURCE_PIN')
        require(form_end(text, r['start']) == r['end'], 'SOURCE_END')
        name = r['operator'].split('::')[1].lower()
        kind = {'macro': 'defmacro', 'compiler-macro': 'define-compiler-macro', 'architecture-dispatch': 'defun'}[r['role']]
        if r['role'] == 'architecture-dispatch':
            name = 'backend-arch-macroexpand'
        require(re.match(r'\('+kind+r'\s+'+re.escape(name)+r'\s', text[r['start']:]), 'SOURCE_DEFINITION')
    expected = '(in-package :ccl-source-expanders)\n(defparameter *selection*\n  \'(' + '\n    '.join(
        f'({r["operator"]} "{r["role"]}" "{r["source"]}" {r["start"]})' for r in rows) + '))\n'
    require((HERE/'selection.lisp').read_text() == expected, 'NATIVE_SELECTION')
    return rows


def functions(f):
    yield f
    for child in f['inner_functions']:
        yield from functions(child)


def helper_sites(f):
    return [(c['site_id'], t['name']) for node in functions(f)
            for c in node['calls'] + node['function_references']
            for t in c['dependency']['targets'] if t['kind'] == 'global-binding']


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def check_probes(p):
    require([r['name'] for r in p] == ['COMMON-LISP::LET*', 'COMMON-LISP::PROGN', 'CCL::BASIC-STREAM-P',
            'local-shadow', 'target-layout', 'CCL::BASIC-STREAM-P', 'alternate-layout'], 'PROBE_BOUND')
    require(p[0]['returned_input'] is True and p[0]['output'] ==
            form(sym('COMMON-LISP::LET*'), form(form(sym('A'), 1)), sym('A')), 'NO_CHANGE_IDENTITY')
    require(p[1] == dict(name='COMMON-LISP::PROGN', output=7, returned_input=False), 'PROGN_PROBE')
    for i, tag in ((2, 50), (5, 122)):
        require(p[i] == dict(name='CCL::BASIC-STREAM-P', output=form(sym('COMMON-LISP::EQL'),
                form(sym('TYPECODE'), sym('A')), tag), returned_input=False), 'LAYOUT_PROBE')
    def ops(tree):
        return [v for v in walk(tree) if 'operator' in v]
    shadow = ops(p[3]['ir'])
    require(Counter(r['operator'] for r in shadow) == {'CCL::LAMBDA-LIST': 1, 'COMMON-LISP::FIXNUM': 1}
            and [elements(r['operands']) for r in shadow if r['operator'] == 'COMMON-LISP::FIXNUM'] == [[42]], 'SHADOW_PRECEDENCE')
    for i, tag in ((4, 50), (6, 122)):
        values = ops(p[i]['ir'])
        require(Counter(r['operator'] for r in values) == {'CCL::LAMBDA-LIST': 1, 'COMMON-LISP::EQ': 1,
                'CCL::IMMEDIATE': 1, 'CCL::TYPECODE': 1, 'NIL': 1, 'COMMON-LISP::FIXNUM': 1}, 'LAYOUT_IR')
        require([elements(r['operands']) for r in values if r['operator'] == 'COMMON-LISP::FIXNUM'] == [[tag]], 'LAYOUT_IR')


def check(c, traversal, selection, reference=False):
    require(c['version'] == 1 and c['macro_environment_qualified'] is False and c['graph_edges_replaced'] == 0, 'SCOPE')
    require(all(c[k] is True for k in ('restored', 'native_pass2_restored', 'bindings_unchanged')), 'RESTORATION')
    check_probes(c['probes'])
    spans = prior.SPANS[:]
    spans += list(dict.fromkeys((r['source'], r['start'], r['end']) for r in selection))
    require([(r['path'], r['start'], r['end']) for r in c['sources']] == spans, 'SOURCE_BOUND')
    for r in c['sources']:
        require(r['key'] == f'{r["path"]}:{r["start"]}' and
                r['text'] == (ROOT/r['path']).read_text()[r['start']:r['end']], 'SOURCE_TEXT')
        prior.previous.base.context(r['reader'])
    keys = [f'{p}:{s}' for p, s, _ in prior.SPANS]
    expected = [('CCL::'+name, 'macro', key) for name, key in zip(prior.NAMES,
                keys[2:6]+[keys[6]]*4+[keys[7]]*6)]
    expected += [(r['operator'], r['role'], f'{r["source"]}:{r["start"]}') for r in selection]
    require([(r['operator'], r['role'], r['source']) for r in c['registry']] == expected, 'REGISTRY_BOUND')
    registry = {(r['operator'], r['role']): r for r in c['registry']}
    alias = {}
    function_ids = {}
    helper_identities = {}
    helper_rows = []
    for r in c['registry']:
        require(type(r['original_id']) is int and type(r['selected_id']) is int and
                r['original_id'] > 0 and r['selected_id'] > 0 and r['original_id'] != r['selected_id'], 'CALLABLE_IDENTITY')
        # The two architecture names intentionally share both functions.
        pair = (r['original_id'], r['selected_id'], r['compiled_function'])
        require(alias.setdefault(r['source'], pair) == pair if r['role'] == 'architecture-dispatch' else True, 'DISPATCH_ALIAS')
        fn = r['compiled_function']
        require(function_ids.setdefault(r['selected_id'], fn) == fn, 'COMPILED_IDENTITY')
        path, start = r['source'].rsplit(':', 1)
        require(r['native_note'] == dict(source='ccl:'+path.replace('/', ';')+'.newest', position=int(start)), 'BINDING_SOURCE')
        require([(h['site_id'], h['name']) for h in r['helpers']] == helper_sites(fn), 'HELPER_JOIN')
        for h in r['helpers']:
            require(h['disposition'] == 'UNQUALIFIED_NATIVE_HELPER' and type(h['function_id']) is int and h['function_id'] > 0,
                    'HELPER_DISPOSITION')
            identity = (h['function_id'], h['note'])
            require(helper_identities.setdefault(h['name'], identity) == identity, 'HELPER_BINDING')
            helper_rows.append(h)
    require(len(function_ids) == 60 and len({r['original_id'] for r in c['registry']}) == 60, 'CALLABLE_BOUND')
    require(len(helper_rows) == 214 and len({h['site_id'] for h in helper_rows}) == 212 and len(helper_identities) == 68, 'HELPER_BOUND')
    unbounded = {e['site_id'] for r in c['registry'] for f in functions(r['compiled_function'])
                 for e in f['calls'] if not e['dependency']['targets']}
    require(len(unbounded) == 4, 'COMPUTED_HELPER_BOUND')
    expected_events = [m for r in traversal['rows'] for m in r['macro_expansions']]
    events = c['events']
    require(len(events) == len(expected_events) == 293 and [r['sequence'] for r in events] == list(range(293)), 'EVENT_BOUND')
    require(Counter(e['role'] for e in events) == {'compiler-macro': 200, 'macro': 91, 'architecture-dispatch': 2}, 'EVENT_ROLES')
    for e, old in zip(events, expected_events):
        require((e['operator'], e['role']) in registry, 'EVENT_BINDING')
        r = registry[e['operator'], e['role']]
        require(e['original_id'] == r['original_id'] and e['source'] == r['source'], 'EVENT_IDENTITY')
        require(e['selected_id'] == r['original_id' if reference else 'selected_id'], 'SOURCE_ROUTING')
        require(e['operator'] == old['operator'] and e['native_note'] ==
                dict(source=old['source'], position=old['position']), 'EVENT_SOURCE_JOIN')
        prior.previous.base.context(e['context'])
        args = elements(e['input'])
        require(args and args[0] == sym(e['operator']), 'EVENT_INPUT')
        if e['operator'] == 'CCL::%GET-KERNEL-GLOBAL-PTR':
            require(e['status'] == 'ESCAPED' and e['output'] is None and e['problem'] ==
                    'No arch-specific macro function for %GET-KERNEL-GLOBAL-PTR in arch :WASM32-CENSUS', 'DISPATCH_REFUSAL')
        else:
            require(e['status'] == 'RETURNED' and e['problem'] is None, 'EXPANSION_STATUS')
        require(type(e['returned_input']) is bool and (not e['returned_input'] or e['input'] == e['output']), 'RETURNED_INPUT')
    refs = {x['object_ref'] for e in events for k in ('input', 'output') for x in walk(e[k]) if 'object_ref' in x}
    require(len(c['literals']) == 3 and {r['id'] for r in c['literals']} == refs, 'LITERAL_BOUND')
    require([(r['type'], r['name'], r['disposition']) for r in c['literals']] ==
            [('CCL::LEXICAL-ENVIRONMENT', None, 'UNQUALIFIED_NATIVE_LITERAL'),
             ('CCL::CLASS-CELL', 'CCL::IOBLOCK', 'UNQUALIFIED_NATIVE_LITERAL'),
             ('CCL::CLASS-WRAPPER', 'COMMON-LISP::RESTART', 'UNQUALIFIED_NATIVE_LITERAL')], 'LITERAL_DISPOSITION')
    counts = prior.previous.check_capture(traversal, (ROOT/'lib/dumplisp.lisp').read_bytes(),
                                          read(HERE.parent/'target-descriptions/descriptions.json'))
    return dict(source_forms=54, registered_bindings=61, compiled_expander_functions=60, routed_events=293,
                source_rebuilt_events=0 if reference else 293, helper_binding_rows=214, helper_sites=212,
                native_helper_names=68, computed_helper_call_sites=4, native_literals=3, **counts)


def compare(c, t, reference, reference_t):
    require(t == reference_t, 'TRAVERSAL_EQUIVALENCE')
    require({k: v for k, v in c.items() if k != 'events'} ==
            {k: v for k, v in reference.items() if k != 'events'}, 'REGISTRY_EQUIVALENCE')
    require([{k: v for k, v in e.items() if k != 'selected_id'} for e in c['events']] ==
            [{k: v for k, v in e.items() if k != 'selected_id'} for e in reference['events']], 'EXPANSION_EQUIVALENCE')


def controls(c, t, reference, reference_t, selection):
    cases = [
        ('omit-source', lambda x: x['sources'].pop(), 'SOURCE_BOUND'),
        ('insert-source', lambda x: x['sources'].append(deepcopy(x['sources'][0])), 'SOURCE_BOUND'),
        ('change-source', lambda x: x['sources'][0].update(text='invented'), 'SOURCE_TEXT'),
        ('omit-binding', lambda x: x['registry'].pop(), 'REGISTRY_BOUND'),
        ('wrong-role', lambda x: x['registry'][15].update(role='macro'), 'REGISTRY_BOUND'),
        ('alias-source', lambda x: x['registry'][0].update(selected_id=x['registry'][0]['original_id']), 'CALLABLE_IDENTITY'),
        ('source-note', lambda x: x['registry'][0]['native_note'].update(position=0), 'BINDING_SOURCE'),
        ('omit-helper', lambda x: next(r for r in x['registry'] if r['helpers'])['helpers'].pop(), 'HELPER_JOIN'),
        ('invent-helper', lambda x: next(r for r in x['registry'] if r['helpers'])['helpers'].append(deepcopy(next(r for r in x['registry'] if r['helpers'])['helpers'][0])), 'HELPER_JOIN'),
        ('promote-helper', lambda x: next(r for r in x['registry'] if r['helpers'])['helpers'][0].update(disposition='QUALIFIED'), 'HELPER_DISPOSITION'),
        ('erase-computed-helper', lambda x: next(e for r in x['registry'] for f in functions(r['compiled_function'])
              for e in f['calls'] if not e['dependency']['targets'])['dependency'].update(targets=[{'kind': 'function', 'id': -1}]), 'COMPUTED_HELPER_BOUND'),
        ('omit-event', lambda x: x['events'].pop(), 'EVENT_BOUND'),
        ('duplicate-event', lambda x: x['events'].append(deepcopy(x['events'][0])), 'EVENT_BOUND'),
        ('native-route', lambda x: x['events'][0].update(selected_id=x['events'][0]['original_id']), 'SOURCE_ROUTING'),
        ('change-event-source', lambda x: x['events'][0].update(source='invented'), 'EVENT_IDENTITY'),
        ('hide-dispatch-refusal', lambda x: next(e for e in x['events'] if e['status']=='ESCAPED').update(status='RETURNED'), 'DISPATCH_REFUSAL'),
        ('omit-literal', lambda x: x['literals'].pop(), 'LITERAL_BOUND'),
        ('promote-literal', lambda x: x['literals'][0].update(disposition='QUALIFIED'), 'LITERAL_DISPOSITION'),
        ('wrong-no-change', lambda x: x['probes'][0].update(returned_input=False), 'NO_CHANGE_IDENTITY'),
        ('wrong-layout', lambda x: x['probes'][2].update(output=0), 'LAYOUT_PROBE'),
        ('omit-probe', lambda x: x['probes'].pop(), 'PROBE_BOUND'),
        ('leave-observer', lambda x: x.update(native_pass2_restored=False), 'RESTORATION'),
        ('promote-environment', lambda x: x.update(macro_environment_qualified=True), 'SCOPE'),
    ]
    results = []
    for name, mutate, expected in cases:
        x = deepcopy(c)
        mutate(x)
        try:
            check(x, t, selection)
        except ValueError as e:
            require(str(e) == expected, f'CONTROL_REASON {name}: {e}')
        else:
            raise ValueError('CONTROL_ESCAPED '+name)
        results.append(dict(id=name, status='REJECTED', reason=expected))
    x = deepcopy(c)
    next(e for e in x['events'] if e['operator'] == 'COMMON-LISP::PROGN')['output'] = 'corrupted expansion'
    try:
        compare(x, t, reference, reference_t)
    except ValueError as e:
        require(str(e) == 'EXPANSION_EQUIVALENCE', 'CONTROL_REASON changed-expansion')
    else:
        raise ValueError('CONTROL_ESCAPED changed-expansion')
    results.append(dict(id='changed-expansion', status='REJECTED', reason='EXPANSION_EQUIVALENCE'))
    for text in ('(a "escaped \\\" )" 1)', '(a ; ) ignored\n 1)', '(#| outer #| inner |# ) |# a)',
                 '(list #\\) 1)', '(list #\\Space 1)'):
        require(form_end(text, 0) == len(text), 'SCANNER_POSITIVE')
    for text, reason in [('(a', 'SOURCE_UNTERMINATED'), ('(#| unfinished', 'SOURCE_COMMENT_EOF'),
                         ('(|escaped|)', 'SOURCE_SCANNER_UNSUPPORTED')]:
        try:
            form_end(text, 0)
        except ValueError as e:
            require(str(e) == reason, 'SCANNER_REFUSAL')
        else:
            raise ValueError('SCANNER_CONTROL_ESCAPED')
        results.append(dict(id='scanner-'+reason.lower(), status='REJECTED', reason=reason))
    return results
