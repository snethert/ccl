"""Independent semantic expectations for the three-layer native corpus."""
from collections import Counter


def check_probe(data):
    summary = data['summary']
    if len(data['sources']) != 3: raise ValueError('three source layers were not observed')
    if not data['emissions'] or any(not r['frames'] for r in data['emissions']):
        raise ValueError('probe emissions lack actual handler identities')
    if not data['fasl_reads'] or any(not r['written'] for r in data['fasl_reads']):
        raise ValueError('probe loaded function has no exact FASL write join')
    if any(r['reader_mode'] != 'native' for r in data['fasl_reads']) or data['image_function_reads']:
        raise ValueError('native probe confused host loading with image construction')
    materialized = {r['function']: r['afunc'] for r in data['materialized']}
    if any(r['written']['function'] not in materialized for r in data['fasl_reads']):
        raise ValueError('serialized function has no compiler materialization join')
    loaded = {r['function'] for r in data['fasl_reads']}
    if any(r['function'] not in loaded for r in data['bindings'] if r['source'] is None
           and r['symbol']['package'] == 'COMMON-LISP-USER'):
        raise ValueError('installed function was not observed in the loader')
    versions = [r for r in data['bindings'] if r['symbol']['name'] == 'RICH-VERSION']
    macros = [r for r in data['bindings'] if r['symbol']['name'] == 'RICH-MACRO']
    for label, rows in [('function', versions), ('macro', macros)]:
        if len(rows) != 6 or len({r['function'] for r in rows}) != 6:
            raise ValueError('missing or collapsed ' + label + ' replacements across compile/load layers')
        if Counter(r['source'].rsplit('/', 1)[-1] if r['source'] else 'load' for r in rows) != {
                'probe-l0.lisp': 1, 'probe-l1.lisp': 1, 'probe-l2.lisp': 1, 'load': 3}:
            raise ValueError('replacement source contexts differ')
    setters = [r for r in data['bindings'] if r['symbol']['setter_of'] == 'COMMON-LISP-USER::RICH-SLOT']
    if len(setters) != 1: raise ValueError('SETF cell identity was not preserved')
    # CCL compiles separate macro expanders for the file's lexical environment,
    # the host binding, and the emitted FASL. Their names agree; their objects
    # must not be collapsed. Join the actual called expander to its own afunc.
    macro_afuncs = {r['function_id'] for r in data['functions'] if r['name'] == 'COMMON-LISP-USER::RICH-MACRO'}
    expanded = [r for r in data['expanders'] if materialized.get(r['function']) in macro_afuncs]
    if len({r['function'] for r in expanded}) != 3 or {
            r['source'].rsplit('/', 1)[-1] for r in expanded} != {'probe-l0.lisp', 'probe-l1.lisp', 'probe-l2.lisp'}:
        raise ValueError('actual lexical macro expander joins are incomplete')
    indirect = [r for r in data['functions'] if r['name'] == 'COMMON-LISP-USER::RICH-INDIRECT']
    if len(indirect) != 1 or not any(not r['dependency']['targets'] for r in indirect[0]['calls']):
        raise ValueError('computed call omitted or disguised as resolved')
    if not data['compile_calls'] or not all(r['function'] in materialized for r in data['compile_calls']):
        raise ValueError('executed compile-time initializer has no compiler identity')
    if not data['load_calls'] or any(r['code_origin']['origin'] != 'exact-fasl-position'
                                     or r['code_origin']['afunc'] is None for r in data['load_calls']):
        raise ValueError('executed loader initializer has no compiler/FASL identity')
    if {r['family'] for r in data['effects']} != {'compile-initializer', 'fasl-effect'}:
        raise ValueError('compile and loader effect completions are both required')
    expected = {event for effect in data['effects'] for event in (effect['enter'], effect['return'])}
    schedule = data['effect_schedule']
    if {r['event'] for r in schedule} != expected or len(schedule) != len(expected):
        raise ValueError('initializer phase schedule omits a real effect boundary')
    previous = {}; last_event = 0
    for rank, row in enumerate(schedule):
        if (row['rank'] != rank or row['event'] <= last_event or
                row['prerequisite_boundary'] != previous.get(row['process'])):
            raise ValueError('initializer order/cycle differs from native execution')
        last_event = row['event']; previous[row['process']] = row['event']
    return {'status': 'PASS', 'function_replacements': 6, 'macro_replacements': 6,
            'serialized_function_joins': len(data['fasl_reads']), 'state_oracle': 'native probe-driver assertions'}
