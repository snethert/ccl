"""Check a source-derived macro slice, without granting environment qualification."""
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('descriptions_analysis', HERE.parent/'target-descriptions/analysis.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
require = previous.require

# Independent spans and field order read from pinned U1, not from the capture.
SPANS = [('level-1/sysutils.lisp', 26953, 27504), ('lib/macros.lisp', 2838, 3451),
         ('library/lispequ.lisp', 2300, 2419), ('library/lispequ.lisp', 2422, 2594),
         ('library/lispequ.lisp', 2678, 2810), ('lib/macros.lisp', 2600, 2640),
         ('library/lispequ.lisp', 45941, 46241), ('library/lispequ.lisp', 48969, 49107)]
SLOTS = {**{'BASIC-STREAM.'+n: i for i, n in enumerate(('WRAPPER', 'FLAGS', 'STATE', 'INFO'))},
         **{'PFE.'+n: i for i, n in enumerate(('ROUTINE-DESCRIPTOR', 'PROC-INFO', 'LISP-FUNCTION',
                                             'SYM', 'WITHOUT-INTERRUPTS', 'TRACE-P'))}}
NAMES = ['GVECTOR', 'ALLOCATE-TYPED-VECTOR', '%ISTRUCT', '%NULL-PTR', *SLOTS]
EXPECTED_USES = Counter({'BASIC-STREAM.STATE': 2, '%ISTRUCT': 2, 'GVECTOR': 2,
                        '%NULL-PTR': 1, 'PFE.SYM': 1, 'PFE.ROUTINE-DESCRIPTOR': 1, 'PFE.PROC-INFO': 1})
NATIVE_CONTROLS = {'host-subtag': 'PROBE_OUTPUT', 'wrong-slot': 'PROBE_OUTPUT',
                   'bypass-source': 'ROUTE_COVERAGE', 'name-only': 'SHADOW_IDENTITY'}


def read(path):
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as f:
        return json.load(f)


def sym(name):
    return {'symbol': name if '::' in name else 'CCL::'+name}


def form(*items):
    result = None
    for item in reversed(items):
        result = {'cons': [item, result]}
    return result


def elements(tree):
    result = []
    while tree is not None:
        require(isinstance(tree, dict) and set(tree) == {'cons'} and len(tree['cons']) == 2, 'PROPER_SYNTAX')
        head, tree = tree['cons']
        result.append(head)
    return result


def expansion(name, call):
    args = elements(call)
    require(args and args[0] == sym(name), 'CALL_OPERATOR')
    args = args[1:]
    if name == 'GVECTOR':
        require(args and args[0] == sym('KEYWORD::ISTRUCT'), 'CALL_TYPE')
        return form(sym('%GVECTOR'), 130, *args[1:])
    if name == 'ALLOCATE-TYPED-VECTOR':
        require(args == [sym('KEYWORD::SIMPLE-VECTOR'), 3, 7], 'ALLOCATION_PROBE')
        return form(sym('%ALLOC-MISC'), 3, 250, 7)
    if name == '%ISTRUCT':
        require(len(args) >= 1, 'ISTRUCT_ARGUMENTS')
        return form(sym('GVECTOR'), sym('KEYWORD::ISTRUCT'), form(sym('REGISTER-ISTRUCT-CELL'), args[0]), *args[1:])
    if name == '%NULL-PTR':
        require(not args, 'NULL_POINTER_ARITY')
        return form(sym('%INT-TO-PTR'), 0)
    require(name in SLOTS and len(args) == 1, 'ACCESSOR_ARGUMENTS')
    return form(sym('%SVREF'), args[0], SLOTS[name])


def walk_ir(x):
    if isinstance(x, dict):
        if 'operator' in x:
            require(set(x) == {'operator', 'operands'}, 'IR_FIELDS')
            yield x
        for v in x.values():
            yield from walk_ir(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk_ir(v)


def check_ir(x, tag, shadow=False):
    ops = list(walk_ir(x))
    expected = Counter({'CCL::LAMBDA-LIST': 1, 'COMMON-LISP::FIXNUM': 1 if shadow else 2})
    if not shadow:
        expected['CCL::%GVECTOR'] = 1
    require(Counter(o['operator'] for o in ops) == expected, 'SHADOW_IDENTITY' if shadow else 'TARGET_IR')
    values = [elements(o['operands']) for o in ops if o['operator'] == 'COMMON-LISP::FIXNUM']
    require(values == ([[42]] if shadow else [[tag], [10]]), 'SHADOW_IDENTITY' if shadow else 'TARGET_IR')


def check(c, traversal):
    require(c['version'] == 1 and c['macro_environment_qualified'] is False, 'SCOPE')
    require(c['restored'] is True and c['global_macro_bindings_unchanged'] is True, 'RESTORATION')
    require([(r['path'], r['start'], r['end']) for r in c['sources']] == SPANS, 'SOURCE_BOUND')
    for row, (path, start, end) in zip(c['sources'], SPANS):
        require(row['key'] == f'{path}:{start}' and row['text'] == (ROOT/path).read_text()[start:end], 'SOURCE_TEXT')
        previous.base.context(row['reader'])
    source_keys = [f'{p}:{s}' for p, s, _ in SPANS]
    keys = source_keys[2:6] + [source_keys[6]]*4 + [source_keys[7]]*6
    require([r['operator'] for r in c['registry']] == ['CCL::'+n for n in NAMES], 'REGISTRY_BOUND')
    all_ids = []
    for name, key, r in zip(NAMES, keys, c['registry']):
        require(r['source'] == key and r['helper'] == ('CCL::TYPE-KEYWORD-CODE' if name in NAMES[:2] else None), 'REGISTRY_SOURCE')
        all_ids.extend([r['original_id'], r['selected_id']])
    require(all(type(i) is int and i > 0 for i in all_ids) and len(set(all_ids)) == len(all_ids), 'CALLABLE_IDENTITIES')
    registry = {r['operator']: r for r in c['registry']}
    probes = c['probes']
    require([p['operator'] for p in probes] == ['CCL::'+n for n in NAMES] +
            ['target-ir', 'local-shadow-ir', 'alternate-subtag', 'missing-subtag'], 'PROBE_BOUND')
    for name, p in zip(NAMES, probes):
        require(p['output'] == expansion(name, p['input']), 'PROBE_OUTPUT')
    check_ir(probes[-4]['output'], 130)
    check_ir(probes[-3]['output'], None, shadow=True)
    require(probes[-2]['output'] == form(sym('%GVECTOR'), 234, 10), 'TARGET_SENSITIVITY')
    check_ir(probes[-2]['ir'], 234)
    require(probes[-1]['condition'] == 'Unknown type-keyword :UNPROVIDED. ', 'MISSING_TYPE_REFUSAL')
    require(Counter(r['operator'].removeprefix('CCL::') for r in c['uses']) == EXPECTED_USES, 'ROUTE_COVERAGE')
    for row in c['uses']:
        r = registry[row['operator']]
        require(all(row[k] == r[k] for k in ('source', 'original_id', 'selected_id')), 'USE_IDENTITY')
        previous.base.context(row['context'])
        require(row['output'] == expansion(row['operator'].removeprefix('CCL::'), row['input']), 'USE_OUTPUT')
    # Every original hook invocation is joined, with order and multiplicity.
    events = c['uses'] + c['remaining']
    require(sorted(r['sequence'] for r in events) == list(range(len(events))), 'EVENT_ORDER')
    expected = [m for row in traversal['rows'] for m in row['macro_expansions']]
    require(len(expected) == len(events) == 293, 'EVENT_BOUND')
    remaining_ids = {}
    for row, original in zip(sorted(events, key=lambda r: r['sequence']), expected):
        require(row['operator'] == original['operator'], 'EVENT_JOIN')
        if 'selected_id' in row:
            path, position = row['source'].split(':')
            logical = 'ccl:'+path.replace('/', ';')+'.newest'
            require(original['source'] == logical and original['position'] == int(position), 'EVENT_SOURCE_JOIN')
        else:
            require(row['source'] == original['source'] and row['position'] == original['position'], 'REMAINING_SOURCE')
            identity = (row['source'], row['position'])
            require(type(row['function_id']) is int and row['function_id'] > 0, 'REMAINING_IDENTITY')
            require(remaining_ids.setdefault(row['function_id'], identity) == identity, 'REMAINING_IDENTITY')
    require(len(remaining_ids) == 46, 'REMAINING_BOUND')
    d = json.loads((HERE.parent/'target-descriptions/descriptions.json').read_text())
    counts = previous.check_capture(traversal, (ROOT/'lib/dumplisp.lisp').read_bytes(), d)
    return dict(source_forms=8, rebuilt_macros=14, used_rebuilt_macros=7, source_routed_expansions=10,
                remaining_expander_identities=46, remaining_expansions=283, **counts)


def controls(c, t):
    cases = [
        ('omit-source', lambda x, y: x['sources'].pop(), 'SOURCE_BOUND'),
        ('invent-source', lambda x, y: x['sources'].append(deepcopy(x['sources'][0])), 'SOURCE_BOUND'),
        ('change-source', lambda x, y: x['sources'][0].update(text='invented'), 'SOURCE_TEXT'),
        ('host-reader', lambda x, y: x['sources'][0]['reader'].update(word_bits=64), 'TARGET_CONTEXT'),
        ('omit-expander', lambda x, y: x['registry'].pop(), 'REGISTRY_BOUND'),
        ('wrong-source', lambda x, y: x['registry'][0].update(source=x['registry'][1]['source']), 'REGISTRY_SOURCE'),
        ('omit-helper', lambda x, y: x['registry'][0].update(helper=None), 'REGISTRY_SOURCE'),
        ('alias-callable', lambda x, y: x['registry'][0].update(selected_id=x['registry'][0]['original_id']), 'CALLABLE_IDENTITIES'),
        ('erase-type-refusal', lambda x, y: x['probes'][-1].update(condition=None), 'MISSING_TYPE_REFUSAL'),
        ('erase-sensitivity', lambda x, y: x['probes'][-2].update(output=form(sym('%GVECTOR'), 130, 10)), 'TARGET_SENSITIVITY'),
        ('erase-ir-sensitivity', lambda x, y: x['probes'][-2].update(ir=x['probes'][-4]['output']), 'TARGET_IR'),
        ('omit-use', lambda x, y: x['uses'].pop(), 'ROUTE_COVERAGE'),
        ('wrong-route', lambda x, y: x['uses'][0].update(selected_id=x['uses'][0]['original_id']), 'USE_IDENTITY'),
        ('wrong-expansion', lambda x, y: x['uses'][0].update(output=0), 'USE_OUTPUT'),
        ('omit-remaining', lambda x, y: x['remaining'].pop(), 'EVENT_BOUND'),
        ('invent-event', lambda x, y: x['remaining'].append(deepcopy(x['remaining'][0])), 'EVENT_ORDER'),
        ('change-event', lambda x, y: x['remaining'][0].update(operator='CCL::INVENTED'), 'EVENT_JOIN'),
        ('change-remaining-source', lambda x, y: x['remaining'][0].update(source='invented'), 'REMAINING_SOURCE'),
        ('no-restoration', lambda x, y: x.update(restored=False), 'RESTORATION'),
        ('promote-environment', lambda x, y: x.update(macro_environment_qualified=True), 'SCOPE'),
    ]
    results = []
    for name, mutate, reason in cases:
        x, y = deepcopy(c), deepcopy(t)
        mutate(x, y)
        try:
            check(x, y)
        except ValueError as e:
            require(str(e) == reason, 'CONTROL_REASON: '+name+': '+str(e))
        else:
            raise ValueError('CONTROL_ESCAPED: '+name)
        results.append(dict(id=name, status='REJECTED', reason=reason))
    return results
