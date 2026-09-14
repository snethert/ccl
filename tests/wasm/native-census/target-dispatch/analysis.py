"""Bound U1 source/lexical joins and independently derive registry transitions."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result
previous = module('dispatch_source_check', HERE.parent/'source-expanders/check.py')
traversal = module('dispatch_traversal_check', HERE.parent/'target-descriptions/analysis.py')
read, require, form, elements = previous.read, previous.require, previous.form, previous.elements
context = traversal.base.context
CONTROLS = {'host-selector': 'TARGET_SELECTION', 'host-fallback': 'MISSING_MACRO_REFUSAL',
            'cached-expander': 'REPLACEMENT_VALUES', 'discard-values': 'MULTIPLE_VALUES'}
SPANS = [('compiler/backend.lisp', 19582, 19960, 'CCL'), ('compiler/arch.lisp', 9368, 9460, 'ARCH'),
         ('compiler/arch.lisp', 8910, 9088, 'ARCH'), ('compiler/arch.lisp', 8774, 8908, 'ARCH')]
ARCH = 'KEYWORD::WASM32-CENSUS'
BATCH, PTR = 'CCL::%GET-KERNEL-GLOBAL', 'CCL::%GET-KERNEL-GLOBAL-PTR'
NAMES = ['original', 'replacement', 'absent', 'present-nil', 'restored', 'pointer-absent',
         'architecture-absent', 'nonlocal', 'after-nonlocal']
def s(x): return {'symbol': x if '::' in x else 'COMMON-LISP::'+x}
def q(x): return form(s('QUOTE'), x)
INPUT = form(s(BATCH), q(s('CCL::BATCH-FLAG')))
POINTER_INPUT = form(s(PTR), q(s('CCL::BATCH-FLAG')))
OUTPUT = form(s('WASM-CENSUS-SERVICES::STARTUP-BATCH-FLAG'))
REPLACEMENT = [q(s('KEYWORD::REPLACEMENT')), s('KEYWORD::SECOND'), s('KEYWORD::THIRD')]


def source_form(text, package):
    """Separate reader for the four simple U1 forms; refuse any other syntax."""
    tokens = re.findall(r';[^\n]*|\s+|"(?:\\.|[^"\\])*"|#\x27|\x27|[()]|[^\s()\x27]+', text)
    require(''.join(tokens) == text, 'SOURCE_TOKENS')
    tokens = [t for t in tokens if not t.isspace() and not t.startswith(';')]
    index = 0
    common = set('DEFUN LET* IF OR ERROR FUNCALL GETHASH CAR MEMBER FUNCTION EQ'.split())
    def parse():
        nonlocal index
        require(index < len(tokens), 'SOURCE_EOF')
        t = tokens[index]; index += 1
        if t == '(':
            rows = []
            while index < len(tokens) and tokens[index] != ')': rows.append(parse())
            require(index < len(tokens), 'SOURCE_CLOSE'); index += 1
            return form(*rows)
        require(t != ')', 'SOURCE_CLOSE')
        if t in ("'", "#'"): return form(s('QUOTE' if t == "'" else 'FUNCTION'), parse())
        if t.startswith('"'):
            # No backslash escapes appear in these four pinned strings.
            require('\\' not in t, 'SOURCE_STRING'); return t[1:-1]
        require(not any(x in t for x in ('#', '|', '\\', '.')), 'SOURCE_SYMBOL')
        t = t.upper()
        if t.startswith(':'): return s('KEYWORD::'+t[1:])
        return s(t if '::' in t else ('COMMON-LISP' if t in common else package)+'::'+t)
    result = parse(); require(index == len(tokens), 'SOURCE_TRAILING'); return result


def compiled(c):
    root = c['compiled']; fs = [root, *root['inner_functions']]
    wanted = ['NIL', 'CCL::BACKEND-ARCH-MACROEXPAND', 'ARCH::ARCH-MACRO-FUNCTION',
              'ARCH::TARGET-ARCH-MACROS', 'ARCH::FIND-TARGET-ARCH']
    require([f['name'] for f in fs] == wanted and all(not f['inner_functions'] for f in fs[1:]), 'PRIVATE_FUNCTION_BOUND')
    ids = {f['name']: f['function_id'] for f in fs}
    require(len(set(ids.values())) == len(ids), 'PRIVATE_FUNCTION_IDENTITY')
    required = {(wanted[0], wanted[1]): 1, (wanted[1], wanted[2]): 1,
                (wanted[2], wanted[3]): 2, (wanted[2], wanted[4]): 1, (wanted[3], wanted[4]): 1}
    found = Counter()
    for f in fs:
        for call in f['calls']:
            dep = call['dependency']
            for target in dep['targets']:
                if target['kind'] == 'function':
                    name = target['name']
                    require(name in ids and target['id'] == ids[name], 'PRIVATE_EDGE_IDENTITY')
                    if dep['category'] == 'lexical': found[(f['name'], name)] += 1
                    else: require(dep['category'] == 'self' and name == f['name'], 'PRIVATE_EDGE_KIND')
                else:
                    require(target['kind'] == 'global-binding' and target['name'] not in wanted[1:], 'GLOBAL_LOOKUP_LEAK')
    require(found == required, 'PRIVATE_EDGE_BOUND')
    return len(fs), sum(found.values())


def lookup(phase, registry, op, fn, present, event=None):
    return dict(kind='lookup', phase=phase, event=event, architecture=ARCH,
                architecture_id=registry['architecture_id'], table_id=registry['table_id'],
                operator=op, function_id=fn, present=present)
def call(phase, fn, inp, env, values, status='RETURNED', event=None):
    return dict(kind='call', phase=phase, event=event, function_id=fn, input=inp,
                environment_id=env, status=status, values=values)
def reason(op): return 'No arch-specific macro function for '+op+' in arch :WASM32-CENSUS'


def check(c, t):
    require(c['version'] == 1 and c['macro_environment_qualified'] is False and c['graph_edges_replaced'] == 0, 'SCOPE')
    require(c['restored'] is True, 'RESTORATION')
    require([(r['path'], r['start'], r['end'], r['package']) for r in c['sources']] == SPANS, 'SOURCE_BOUND')
    for r in c['sources']:
        context(r['reader']); text = (ROOT/r['path']).read_text()
        require(r['text'] == text[r['start']:r['end']] and previous.form_end(text, r['start']) == r['end'], 'SOURCE_TEXT')
        require(r['form'] == source_form(r['text'], r['package']), 'SOURCE_FORM')
    functions, edges = compiled(c)
    reg, file_reg = c['probe_registry'], c['file_registry']
    require(file_reg == dict(architecture=ARCH, architecture_id=file_reg['architecture_id'],
        table_id=file_reg['table_id'], original_id=reg['original_id'], batch_is_description=True,
        pointer_id=None, pointer_present=False, registered=True), 'FILE_REGISTRY')
    require(reg['architecture'] == ARCH and reg['host_architecture'] == 'KEYWORD::X8664', 'REGISTRY_ARCHITECTURE')
    identities = [reg[k] for k in ('architecture_id', 'table_id', 'original_id', 'replacement_id',
                                 'escaping_id', 'environment_id', 'host_batch_id', 'host_pointer_id')]
    identities += [file_reg['architecture_id'], file_reg['table_id'], c['selected_id']]
    require(all(type(n) is int and n > 0 for n in identities) and len(set(identities)) == len(identities), 'REGISTRY_IDENTITY')
    events = c['events']
    require(len(events) == 293 and [e['sequence'] for e in events] == list(range(293)), 'EVENT_BOUND')
    require([e['operator'] for e in events] == [e['operator'] for r in t['rows'] for e in r['macro_expansions']], 'FILE_EVENT_JOIN')
    selected = [e for e in events if e['role'] == 'architecture-dispatch']
    require([e['sequence'] for e in selected] == [182, 191], 'DISPATCH_EVENT_BOUND')
    for e in selected:
        context(e['context'])
        require(e['selected_id'] == c['selected_id'] and e['original_id'] != c['selected_id'] and e['source'] == 'compiler/backend.lisp:19582', 'FILE_ROUTING')
    pointer, batch = selected
    require(pointer['input'] == form(s(PTR), q(s('CCL::KERNEL-PATH')), s('CCL::P')) and
            pointer['operator'] == PTR and pointer['status'] == 'ESCAPED' and pointer['output'] is None and
            pointer['problem'] == reason('%GET-KERNEL-GLOBAL-PTR'), 'FILE_POINTER_REFUSAL')
    require(batch['operator'] == BATCH and batch['input'] == INPUT and batch['output'] == OUTPUT and
            batch['status'] == 'RETURNED' and batch['problem'] is None, 'FILE_BATCH_RESULT')
    trace = c['file_trace']; require(len(trace) == 3, 'FILE_TRACE_BOUND')
    expected = [lookup('dumplisp', file_reg, PTR, None, False, 182),
                lookup('dumplisp', file_reg, BATCH, reg['original_id'], True, 191),
                call('dumplisp', reg['original_id'], INPUT, trace[2]['environment_id'], [OUTPUT], event=191)]
    require(type(trace[2]['environment_id']) is int and trace[2]['environment_id'] > 0 and trace == expected, 'FILE_LOOKUP_CALL_JOIN')
    require([p['name'] for p in c['probes']] == NAMES, 'PROBE_BOUND')
    expected_trace = []
    for p in c['probes']:
        name = p['name']; fn = reg['original_id']; vals = [OUTPUT]
        inp, op = (POINTER_INPUT, PTR) if name == 'pointer-absent' else (INPUT, BATCH)
        env = reg['environment_id']
        if name == 'nonlocal':
            require(p == dict(name=name, escaped=True, binding_restored=True), 'NONLOCAL_RESTORATION')
            expected_trace += [lookup(name, reg, BATCH, reg['escaping_id'], True),
                               call(name, reg['escaping_id'], INPUT, env, None, 'ESCAPED')]
            continue
        require(p['input'] == inp and p['environment_id'] == env, 'PROBE_INPUT')
        if name in ('absent', 'present-nil', 'pointer-absent', 'architecture-absent'):
            problem = 'unknown arch: :WASM32-CENSUS' if name == 'architecture-absent' else reason(op)
            require(p == dict(name=name, input=inp, environment_id=env, status='ERROR', values=None, problem=problem), 'MISSING_MACRO_REFUSAL')
            if name != 'architecture-absent': expected_trace.append(lookup(name, reg, op, None, name == 'present-nil'))
            continue
        if name == 'replacement':
            fn, vals = reg['replacement_id'], REPLACEMENT
            require(p['values'] and p['values'][0] == vals[0], 'REPLACEMENT_VALUES')
            require(p['values'] == vals, 'MULTIPLE_VALUES')
        else: require(p['values'] == vals, 'TARGET_SELECTION')
        require(p == dict(name=name, input=inp, environment_id=env, status='RETURNED', values=vals, problem=None), 'PROBE_RETURN')
        expected_trace += [lookup(name, reg, op, fn, True), call(name, fn, inp, env, vals)]
    require(c['probe_trace'] == expected_trace, 'PROBE_LOOKUP_CALL_JOIN')
    reference = c['reference_probes']; reference_reg = c['reference_registry']
    require([p['name'] for p in reference] == NAMES and reference_reg['original_id'] == reg['original_id'] and
            reference_reg['replacement_id'] == reg['replacement_id'] and
            reference_reg['escaping_id'] == reg['escaping_id'], 'REFERENCE_REGISTRY')
    for actual, native in zip(c['probes'], reference):
        if 'environment_id' in native:
            require(native['environment_id'] == reference_reg['environment_id'] and
                    native['environment_id'] != reg['environment_id'], 'REFERENCE_ENVIRONMENT')
        require({k: v for k, v in actual.items() if k != 'environment_id'} ==
                {k: v for k, v in native.items() if k != 'environment_id'}, 'NATIVE_REFERENCE')
    counts = traversal.check_capture(t, (ROOT/'lib/dumplisp.lisp').read_bytes(), read(HERE.parent/'target-descriptions/descriptions.json'))
    return dict(source_functions=4, compiled_functions=functions, private_call_edges=edges,
                architecture_macro_events=2, file_lookup_records=2, file_computed_calls=1,
                registry_probes=9, native_reference_probes=9, returned_probes=4, refusal_probes=4, nonlocal_probes=1,
                probe_lookup_records=8, probe_computed_calls=5, **counts)


def controls(c, t):
    cases = [
        ('reference-result', 'NATIVE_REFERENCE', lambda x: x['reference_probes'][0].update(values=[None])),
        ('scope', 'SCOPE', lambda x: x.update(macro_environment_qualified=True)),
        ('restore', 'RESTORATION', lambda x: x.update(restored=False)),
        ('source-omit', 'SOURCE_BOUND', lambda x: x['sources'].pop()),
        ('source-text', 'SOURCE_TEXT', lambda x: x['sources'][0].update(text='changed')),
        ('source-package-read', 'SOURCE_FORM', lambda x: x['sources'][1].update(form=None)),
        ('private-function-omit', 'PRIVATE_FUNCTION_BOUND', lambda x: x['compiled']['inner_functions'].pop()),
        ('private-edge-id', 'PRIVATE_EDGE_IDENTITY', lambda x: x['compiled']['calls'][0]['dependency']['targets'][0].update(id=-1)),
        ('file-registry', 'FILE_REGISTRY', lambda x: x['file_registry'].update(batch_is_description=False)),
        ('host-target-alias', 'REGISTRY_IDENTITY', lambda x: x['probe_registry'].update(host_batch_id=x['probe_registry']['original_id'])),
        ('file-event-omit', 'EVENT_BOUND', lambda x: x['events'].pop()),
        ('file-routing', 'FILE_ROUTING', lambda x: x['events'][191].update(selected_id=-1)),
        ('pointer-fallback', 'FILE_POINTER_REFUSAL', lambda x: x['events'][182].update(status='RETURNED')),
        ('file-edge-insert', 'FILE_TRACE_BOUND', lambda x: x['file_trace'].append(x['file_trace'][-1])),
        ('file-wrong-table', 'FILE_LOOKUP_CALL_JOIN', lambda x: x['file_trace'][0].update(table_id=-1)),
        ('file-wrong-callee', 'FILE_LOOKUP_CALL_JOIN', lambda x: x['file_trace'][2].update(function_id=x['probe_registry']['host_batch_id'])),
        ('probe-omit', 'PROBE_BOUND', lambda x: x['probes'].pop()),
        ('stale-replacement', 'REPLACEMENT_VALUES', lambda x: x['probes'][1].update(values=[OUTPUT])),
        ('drop-value', 'MULTIPLE_VALUES', lambda x: x['probes'][1]['values'].pop()),
        ('missing-return', 'MISSING_MACRO_REFUSAL', lambda x: x['probes'][2].update(status='RETURNED')),
        ('lost-throw', 'NONLOCAL_RESTORATION', lambda x: x['probes'][7].update(escaped=False)),
        ('probe-edge-insert', 'PROBE_LOOKUP_CALL_JOIN', lambda x: x['probe_trace'].append(x['probe_trace'][0])),
        ('probe-edge-omit', 'PROBE_LOOKUP_CALL_JOIN', lambda x: x['probe_trace'].pop()),
        ('nil-presence', 'PROBE_LOOKUP_CALL_JOIN', lambda x: next(r for r in x['probe_trace'] if r['phase']=='present-nil').update(present=False)),
        ('call-environment', 'PROBE_LOOKUP_CALL_JOIN', lambda x: x['probe_trace'][1].update(environment_id=-1)),
    ]
    outcomes = []
    for name, reason, mutate in cases:
        changed = deepcopy(c); mutate(changed)
        try: check(changed, t)
        except ValueError as e: require(str(e) == reason, 'WRONG_CONTROL '+name+': '+str(e))
        else: raise ValueError('CONTROL_ESCAPED '+name)
        outcomes.append(dict(name=name, status='REJECTED', reason=reason))
    return outcomes
