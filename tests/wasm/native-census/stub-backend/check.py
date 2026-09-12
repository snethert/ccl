"""Literal-offset/width, reader and real-IR oracle for the census registration proof."""
EXPECTED = {
    'WORD-WIDTH': ['COMMON-LISP::FIXNUM', '32'],
    'FIXNUM-SHIFT': ['COMMON-LISP::FIXNUM', '2'],
    'CONS-TAG': ['COMMON-LISP::FIXNUM', '1'],
    'MISC-TAG': ['COMMON-LISP::FIXNUM', '6'],
    'READER-FEATURE': ['CCL::IMMEDIATE', 'KEYWORD::WASM'],
    'READER-WIDTH': ['COMMON-LISP::FIXNUM', '32'],
    'BORROWED-NATIVE-FEATURE': ['CCL::IMMEDIATE', 'KEYWORD::ISOLATED'],
    'HOST-FEATURE': ['CCL::IMMEDIATE', 'KEYWORD::ISOLATED'],
    'MACRO-CAPTURE': ['COMMON-LISP::FIXNUM', '32'],
    'FIXNUM-BOUNDARY': ['CCL::IMMEDIATE', '536870912'],
}


def check(report):
    if report['during'] != ['KEYWORD::WASM32-CENSUS', 'WASM-CENSUS', 'WASM-CENSUS-OS', 'KEYWORD::WASM32-CENSUS', True]:
        raise ValueError('target/package/foreign-data state differs before reading')
    if report['restored_normal_and_escape'] is not True:
        raise ValueError('target context did not restore native state')
    rows = {r['name']: r for r in report['rows']}
    if len(rows) != len(report['rows']) or set(rows) != set(EXPECTED) | {'NATURAL-ACCESS', 'B-ARGUMENTS', 'LEXICAL-CALL', 'DYNAMIC-CALL'}:
        raise ValueError('source case omitted or duplicated')
    for name, value in EXPECTED.items():
        if rows[name]['literals'] != [value]:
            raise ValueError('wrong target constant/reader/macro result: ' + name)
    if report['natural_macro_operator'] != 'CCL::%GET-UNSIGNED-LONG':
        raise ValueError('natural-width macro inherited the host')
    # The macro must also reach the corresponding real front-end operation.
    if rows['NATURAL-ACCESS']['memory_access_flags'] != [4]:
        raise ValueError('natural-width lowering differs in real acode')
    if rows['B-ARGUMENTS']['argument_partitions'] != [[5, 0]]:
        raise ValueError('B arguments partitioned into native registers')
    direct = rows['B-ARGUMENTS']['function']['calls']
    if len(direct) != 1 or direct[0]['dependency'] != {
            'category': 'global-binding', 'targets': [{'kind': 'global-binding', 'name': 'CCL-CENSUS-STUB::CENSUS-SINK'}]}:
        raise ValueError('direct dependency lost')
    lexical = rows['LEXICAL-CALL']['function']
    children = {c['function_id']: c for c in lexical['inner_functions']}
    call = lexical['calls'][0]['dependency']
    if call['category'] != 'lexical' or len(call['targets']) != 1 or call['targets'][0]['id'] not in children:
        raise ValueError('lexical dependency missing or rebound')
    child = children[call['targets'][0]['id']]
    if not any(c['dependency'] == direct[0]['dependency'] for c in child['calls']):
        raise ValueError('lexical child dependency omitted')
    dynamic = rows['DYNAMIC-CALL']['function']['calls']
    if len(dynamic) != 1 or dynamic[0]['dependency']['category'] != 'function-variable' or dynamic[0]['dependency']['targets']:
        raise ValueError('unresolved dynamic dependency concealed or fabricated')
    return len(rows)
