"""Check source-derived numeric/layout helper paths; retain other dependencies."""
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('source_expanders', HERE.parent/'source-expanders/check.py')
previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
require, sym, form, elements = previous.require, previous.sym, previous.form, previous.elements
context = previous.prior.previous.base.context
SPANS = [('compiler/optimizers.lisp', 7408, 7953, False), ('compiler/optimizers.lisp', 7408, 7953, True),
         ('compiler/nx0.lisp', 80372, 80629, False), ('compiler/nx0.lisp', 27546, 27807, False),
         ('compiler/optimizers.lisp', 20905, 21052, False), ('compiler/optimizers.lisp', 75294, 75408, False),
         ('compiler/optimizers.lisp', 71635, 72010, False)]
NAMES = ['zero', 'maximum-fixnum', 'minimum-fixnum', 'positive-boxed-integer', 'negative-boxed-integer',
         'large-integer', 'single-float', 'double-float', 'stream-subtag', 'stream-subtag',
         'target-range', 'alternate-range', 'missing-subtag']
CONTROLS = {'inherited': 'BOXED_INTEGER_LOWERING', 'host-reader': 'SINGLE_FLOAT_LOWERING',
            'host-range': 'BOXED_INTEGER_LOWERING', 'host-subtag': 'TARGET_SUBTAG'}


def read(p):
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def check(c, traversal):
    require(c['version'] == 1 and c['macro_environment_qualified'] is False and c['graph_edges_replaced'] == 0, 'SCOPE')
    require(c['restored'] is True and c['global_helpers_unchanged'] is True, 'RESTORATION')
    require([(s['path'], s['start'], s['end'], s['host_reader']) for s in c['sources']] == SPANS, 'SOURCE_BOUND')
    for s in c['sources']:
        text = (ROOT/s['path']).read_text()
        require(previous.form_end(text, s['start']) == s['end'] and s['text'] == text[s['start']:s['end']], 'SOURCE_TEXT')
        if not s['host_reader']: context(s['reader'])
        else: require(s['reader']['word_bits'] == 64, 'HOST_CONTROL_READER')
    # Target reading removes the SINGLE-FLOAT branch; the host-read control keeps it.
    has_float = lambda s: any(x.get('symbol') == 'COMMON-LISP::SINGLE-FLOAT' for x in previous.walk(s['form']))
    require(not has_float(c['sources'][0]) and has_float(c['sources'][1]), 'READER_CONDITIONAL')
    p = c['probes']; require([r['name'] for r in p] == NAMES, 'PROBE_BOUND')
    values = [0, 536870911, -536870912, 536870912, -536870913, 1152921504606846976,
              dict(float='COMMON-LISP::SINGLE-FLOAT', significand=8388608, exponent=-23, sign=1),
              dict(float='COMMON-LISP::DOUBLE-FLOAT', significand=4503599627370496, exponent=-52, sign=1)]
    for i, (r, value) in enumerate(zip(p, values)):
        expected_input = form(sym('COMMON-LISP::EQL'), sym('CCL::X'), value)
        eq = i < 3
        reason = 'SINGLE_FLOAT_LOWERING' if i == 6 else 'BOXED_INTEGER_LOWERING' if i in (3, 4, 5) else 'NUMERIC_LOWERING'
        require(r['input'] == expected_input and r['expansion'] == form(sym('COMMON-LISP::EQ' if eq else 'COMMON-LISP::EQL'), sym('CCL::X'), value)
                and r['returned_input'] is (not eq), reason)
        calls = r['function']['calls']
        if eq:
            require(r['operators'].count('COMMON-LISP::EQ') == 1 and calls == [], 'PROBE_ACODE')
        else:
            require('COMMON-LISP::EQ' not in r['operators'] and len(calls) == 1 and calls[0]['dependency'] ==
                    dict(category='builtin', builtin_index=10, targets=[dict(kind='global-binding', name='COMMON-LISP::EQL')]), 'PROBE_ACODE')
    for r, tag in zip(p[8:10], (50, 122)):
        require(r['tag'] == tag and r['expansion'] == form(sym('COMMON-LISP::EQL'), form(sym('CCL::TYPECODE'), sym('CCL::X')), tag), 'TARGET_SUBTAG')
    require(p[10] == dict(name='target-range', word_bits=32, fixnum_shift=2, low=-(2**29), high=2**29-1), 'TARGET_RANGE')
    require(p[11]['expansion'] == form(sym('COMMON-LISP::EQL'), sym('CCL::X'), 8), 'DYNAMIC_TARGET_RANGE')
    require(p[12]['condition'] == 'While compiling an anonymous function :\nType :BASIC-STREAM not supported on target :WASM32-CENSUS' and
            p[12]['restored_expansion'] == p[8]['expansion'], 'MISSING_DESCRIPTOR')
    require(len(c['compiled']) == 5 and len({r['id'] for r in c['compiled']}) == 5 and
            all(r['function'] for r in c['compiled']), 'COMPILED_BOUND')
    expected_entries = [('COMMON-LISP::EQL', c['compiled'][0]['id']),
                        ('CCL::BASIC-STREAM-P', c['compiled'][3]['id']), ('COMMON-LISP::VECTORP', c['compiled'][4]['id'])]
    require([(e['operator'], e['selected_id']) for e in c['selected_entries']] == expected_entries, 'PRIVATE_ROUTING')
    selected = dict(expected_entries)
    events = sorted(c['events'], key=lambda e: e['sequence'])
    require(len(events) == 293 and [e['sequence'] for e in events] == list(range(293)), 'EVENT_BOUND')
    original = [m for r in traversal['rows'] for m in r['macro_expansions']]
    require(len(original) == len(events) and all(e['operator'] == m['operator'] for e, m in zip(events, original)), 'EVENT_JOIN')
    for e in events:
        context(e['context'])
        if e['operator'] in selected: require(e['selected_id'] == selected[e['operator']], 'EVENT_ROUTING')
    require(Counter(e['operator'] for e in events if e['operator'] in selected) ==
            {'COMMON-LISP::EQL': 17, 'CCL::BASIC-STREAM-P': 2, 'COMMON-LISP::VECTORP': 2}, 'ROUTED_MACRO_BOUND')
    require(Counter((r['phase'], r['helper']) for r in c['calls']) == {
        ('dumplisp', 'EQL-IFF-EQ-P'): 34, ('dumplisp', 'NX-LOOKUP-TARGET-UVECTOR-SUBTAG'): 6,
        ('probe', 'EQL-IFF-EQ-P'): 32, ('probe', 'NX-LOOKUP-TARGET-UVECTOR-SUBTAG'): 2,
        ('descriptor-probe', 'EQL-IFF-EQ-P'): 2, ('descriptor-probe', 'NX-LOOKUP-TARGET-UVECTOR-SUBTAG'): 1}, 'HELPER_CALL_BOUND')
    for r in c['calls']:
        context(r['target'])
        if r['helper'] == 'EQL-IFF-EQ-P': require(type(r['answer']) is bool, 'HELPER_RETURN')
        else:
            tags = {'KEYWORD::BASIC-STREAM': (50, 122), 'KEYWORD::VECTOR-HEADER': (242,), 'KEYWORD::MIN-CL-IVECTOR-SUBTAG': (159,)}
            require(r['value'] in tags[r['input']['symbol']], 'HELPER_RETURN')
    by_event = {}
    for row in c['calls']:
        if row['phase'] == 'dumplisp': by_event.setdefault(row['event'], []).append(row)
        else: require(row['event'] is None, 'HELPER_EVENT_DOMAIN')
    require(set(by_event) == {e['sequence'] for e in events if e['operator'] in selected}, 'HELPER_EVENT_JOIN')
    for event in events:
        if event['operator'] not in selected: continue
        calls = by_event[event['sequence']]
        if event['operator'] == 'COMMON-LISP::EQL':
            args = elements(event['input'])[1:]
            require(calls[0]['input'] == args[0] and calls[0]['helper'] == 'EQL-IFF-EQ-P', 'HELPER_EVENT_JOIN')
            if calls[0]['answer']:
                require(len(calls) == 1, 'HELPER_SHORT_CIRCUIT')
            else:
                require(len(calls) == 2 and calls[1]['input'] == args[1] and
                        calls[1]['helper'] == 'EQL-IFF-EQ-P', 'HELPER_EVENT_JOIN')
            folded = any(r['answer'] for r in calls)
            require(event['output'] == (form(sym('COMMON-LISP::EQ'), *args) if folded else event['input']) and
                    event['returned_input'] is (not folded), 'HELPER_EXPANSION_JOIN')
        else:
            wanted = [('KEYWORD::BASIC-STREAM', 50)] if event['operator'] == 'CCL::BASIC-STREAM-P' else [
                ('KEYWORD::VECTOR-HEADER', 242), ('KEYWORD::MIN-CL-IVECTOR-SUBTAG', 159)]
            require([(r['input']['symbol'], r['value']) for r in calls] == wanted and
                    all(r['helper'] == 'NX-LOOKUP-TARGET-UVECTOR-SUBTAG' for r in calls), 'HELPER_EVENT_JOIN')
    counts = previous.prior.previous.check_capture(traversal, (ROOT/'lib/dumplisp.lisp').read_bytes(),
                                                   read(HERE.parent/'target-descriptions/descriptions.json'))
    return dict(source_forms=6, source_reads=7, rewritten_macro_entries=3, numeric_probes=8,
                descriptor_probes=5, file_helper_calls=40, full_macro_environment_qualified=False, **counts)


def controls(c, traversal):
    cases = [
        ('promote-scope', 'SCOPE', lambda x: x.update(macro_environment_qualified=True)),
        ('omit-source', 'SOURCE_BOUND', lambda x: x['sources'].pop()),
        ('replace-source', 'SOURCE_TEXT', lambda x: x['sources'][0].update(text='wrong')),
        ('omit-numeric-probe', 'PROBE_BOUND', lambda x: x['probes'].pop(0)),
        ('replace-builtin', 'PROBE_ACODE', lambda x: x['probes'][3]['function']['calls'][0]['dependency']['targets'][0].update(name='COMMON-LISP::EQUAL')),
        ('freeze-range', 'DYNAMIC_TARGET_RANGE', lambda x: x['probes'][11].update(expansion=form(sym('COMMON-LISP::EQ'), sym('CCL::X'), 8))),
        ('erase-missing-descriptor', 'MISSING_DESCRIPTOR', lambda x: x['probes'][12].update(condition=None)),
        ('omit-compiled', 'COMPILED_BOUND', lambda x: x['compiled'].pop()),
        ('bypass-private-entry', 'PRIVATE_ROUTING', lambda x: x['selected_entries'][0].update(selected_id=x['compiled'][1]['id'])),
        ('omit-expansion-event', 'EVENT_BOUND', lambda x: x['events'].pop()),
        ('omit-helper-call', 'HELPER_CALL_BOUND', lambda x: x['calls'].pop()),
        ('invent-helper-call', 'HELPER_CALL_BOUND', lambda x: x['calls'].append(deepcopy(x['calls'][0]))),
        ('wrong-helper-parent', 'HELPER_EVENT_JOIN', lambda x: x['calls'][0].update(event=-1)),
        ('wrong-helper-answer', 'HELPER_EXPANSION_JOIN', lambda x: next(r for r in x['calls'] if r['phase']=='dumplisp' and r.get('answer') is True).update(answer=False)),
        ('lose-restoration', 'RESTORATION', lambda x: x.update(restored=False))]
    results = []
    for name, reason, mutate in cases:
        value = deepcopy(c); mutate(value)
        try: check(value, traversal)
        except ValueError as e: require(str(e) == reason, 'WRONG_CONTROL_REASON '+name+': '+str(e))
        else: raise ValueError('CONTROL_ESCAPED '+name)
        results.append(dict(name=name, status='REJECTED', reason=reason))
    return results
