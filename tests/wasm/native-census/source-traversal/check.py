"""Coverage and dependency checks for the pinned first-module traversal."""
from collections import Counter
import hashlib

SOURCE_SHA256 = '5cd12bcbfe6164874e4cefdbd6583612725d8cd773f5d970c66b956097408b74'
# Independent U1 source inventory, not a count copied from the collector.
NAMES = [None, 'CCL::*SAVE-EXIT-FUNCTIONS*', 'CCL::*RESTORE-LISP-FUNCTIONS*', None] + [
    'CCL::' + n for n in ('KILL-LISP-POINTERS', 'CLEAR-IOBLOCK-STREAMS', 'SAVE-APPLICATION',
    '%SAVE-APPLICATION-INTERNAL', 'SAVE-IMAGE', 'SKIP-EMBEDDED-IMAGE', '%PREPEND-FILE',
    'KERNEL-PATH', 'OPEN-DUMPLISP-FILE', '%SAVE-APPLICATION', 'RESTORE-LISP-POINTERS',
    'RESTORE-PASCAL-FUNCTIONS')]
OPERATORS = ['COMMON-LISP::' + n for n in ['IN-PACKAGE', 'DEFVAR', 'DEFVAR', 'DECLAIM'] + ['DEFUN'] * 12]
# End offsets of the sixteen forms in the fixed ASCII source above. This source
# oracle is intentionally independent of both mutable copies of the read index.
ENDS = [688, 789, 893, 947, 1276, 2660, 5219, 7550, 8802, 10385, 12716, 13142, 14447, 14594, 15856, 16350]
FAILURES = {6: ('front-end', ':BASIC-STREAM'), 9: ('read', 'WASM-CENSUS-OS::|exit|'),
            10: ('read', 'SEEK_END'), 11: ('read', 'SEEK_SET'),
            12: ('front-end', '%GET-KERNEL-GLOBAL-PTR'), 13: ('read', 'O_RDONLY'),
            15: ('front-end', '%GET-KERNEL-GLOBAL'), 16: ('front-end', ':VECTOR-HEADER')}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def functions(f):
    yield f
    for child in f['inner_functions']:
        yield from functions(child)


def context(c):
    require(c['backend'] == 'KEYWORD::WASM32-CENSUS' and c['target_package'] == 'WASM-CENSUS'
            and c['os_package'] == 'WASM-CENSUS-OS' and c['fasl_target'] == 'KEYWORD::WASM32-CENSUS'
            and c['foreign_data_matches'] is True and c['word_bits'] == 32 and c['argument_registers'] == 0,
            'TARGET_CONTEXT')
    f = set(c['features'])
    require({'KEYWORD::WASM-TARGET', 'KEYWORD::WASM32-TARGET', 'KEYWORD::32-BIT-TARGET',
             'KEYWORD::LITTLE-ENDIAN-TARGET'} <= f and
            not any(n in f for n in ['KEYWORD::64-BIT-TARGET', 'KEYWORD::DARWIN-TARGET',
                                     'KEYWORD::X86-TARGET', 'KEYWORD::X8664-TARGET']), 'TARGET_FEATURES')


def check_capture(c, source):
    require(hashlib.sha256(source).hexdigest() == SOURCE_SHA256, 'SOURCE_IDENTITY')
    text = source.decode('ascii')  # Offsets are characters; this pinned source is ASCII.
    require(c['version'] == 1 and c['source'] == 'lib/dumplisp.lisp', 'CAPTURE_PROFILE')
    require(c['characters'] == c['eof'] == len(text), 'SOURCE_EOF')
    require(c['native_state_restored'] is True and c['source_bindings_unchanged'] is True, 'NATIVE_RESTORATION')
    context(c['target'])
    index, rows = c['index'], c['rows']
    require(len(index) == len(rows) == 16, 'FORM_COVERAGE')
    require([r['name'] for r in index] == NAMES and [r['operator'] for r in index] == OPERATORS, 'SOURCE_FORM_INVENTORY')
    require([r['end'] for r in index] == ENDS, 'SOURCE_FORM_SPANS')
    position = 0
    prior = []
    all_functions = []
    for ordinal, (entry, row) in enumerate(zip(index, rows), 1):
        require(entry['ordinal'] == row['ordinal'] == ordinal, 'FORM_ORDER')
        require(entry['start'] == row['start'] == position and entry['end'] == row['end'] and
                position < row['end'] <= len(text), 'FORM_RANGES')
        position = row['end']
        context(row['reader_context'])
        require(row['prior_unresolved_forms'] == prior, 'PRIOR_UNRESOLVED_FORMS')
        if ordinal in FAILURES:
            stage, marker = FAILURES[ordinal]
            require(row['status'] == 'UNSUPPORTED' and row['function'] is None and row['problem'] and
                    row['problem']['stage'] == stage and marker in row['problem']['message'], 'UNSUPPORTED_OBLIGATION')
            prior.append(ordinal)
            if stage == 'read':
                require(row['operator'] is None and row['name'] is None, 'FAILED_READ_PROMOTION')
                continue
        else:
            require(row['problem'] is None, 'UNEXPECTED_PROBLEM')
            if ordinal in (2, 3):
                require(row['status'] == 'TOPLEVEL-PROCESSED' and row['function'] is None and
                        row['deferred_output_opcodes'], 'DECLARATION_PROCESSING')
            else:
                require(row['status'] == 'CAPTURED' and row['function'], 'FUNCTION_CAPTURE')
                require(row['function']['name'] == (entry['name'] or 'NIL'), 'DEFINITION_IDENTITY')
                all_functions.extend(functions(row['function']))
        require(row['operator'] == entry['operator'] and row['name'] == entry['name'], 'TARGET_FORM_IDENTITY')
        require(any(m['operator'] == entry['operator'] and m['backend'] == 'KEYWORD::WASM32-CENSUS'
                    for m in row['macro_expansions']), 'MACRO_WITNESS')
    require(position == c['tail_start'] and not text[position:].strip(), 'SOURCE_TAIL')
    ids = [f['function_id'] for f in all_functions]
    require(len(ids) == len(set(ids)) == 12, 'FUNCTION_IDENTITIES')
    sites = []
    for f in all_functions:
        for child in f['inner_functions']:
            require(child['parent_id'] == f['function_id'], 'LEXICAL_PARENT')
        for row in f['calls'] + f['function_references']:
            sites.append(row['site_id'])
            for target in row['dependency']['targets']:
                if target['kind'] == 'function':
                    require(target['id'] in ids, 'LEXICAL_TARGET')
                else:
                    require(target['kind'] == 'global-binding' and target['name'], 'NAMED_TARGET')
    require(len(sites) == len(set(sites)), 'SITE_IDENTITIES')
    # Call obligations read directly from U1, independent of output counts.
    for name, wanted in {'CCL::KILL-LISP-POINTERS': 'CCL::CLEAR-OPEN-FILE-STREAMS',
                         'CCL::%SAVE-APPLICATION': 'CCL::%%SAVE-APPLICATION'}.items():
        f = next(f for f in all_functions if f['name'] == name)
        require(any(t.get('name') == wanted for c in f['calls'] for t in c['dependency']['targets']), 'SOURCE_CALL_WITNESS')
    return {'top_level_forms': 16, 'function_definitions': 12, 'captured_definitions': 4,
            'unsupported_definitions': 8, 'captured_initializer_bodies': 2, 'code_prototypes': len(ids),
            'call_sites': sum(len(f['calls']) for f in all_functions),
            'function_reference_sites': sum(len(f['function_references']) for f in all_functions),
            'unresolved_calls': sum(not c['dependency']['targets'] for f in all_functions for c in f['calls'])}


def project(capture):
    """Facts for later integration, with no implicit module-to-member edges."""
    definitions, calls, refs, gaps = [], [], [], []
    for row in capture['rows']:
        if row['problem']:
            gaps.append({'form': row['ordinal'], 'source_name': capture['index'][row['ordinal']-1]['name'], **row['problem']})
        if row['function']:
            for f in functions(row['function']):
                definitions.append({'id': f['function_id'], 'parent': f['parent_id'], 'name': f['name'],
                                    'form': row['ordinal'], 'start': row['start'], 'end': row['end'],
                                    'operators': f['operators'], 'variables': f['variables'],
                                    'prior_unresolved_forms': row['prior_unresolved_forms']})
                for field, dest in [('calls', calls), ('function_references', refs)]:
                    for site in f[field]:
                        dest.append({'function': f['function_id'], 'form': row['ordinal'], 'site': site['site_id'],
                                     'record': site, 'qualification': 'UNQUALIFIED_TARGET_DEPENDENCY'})
    return {'version': 1, 'status': 'PARTIAL_SOURCE_FACTS', 'source': capture['source'],
            'source_sha256': SOURCE_SHA256, 'namespace': 'dumplisp-target-traversal',
            'definitions': definitions, 'calls': calls, 'function_references': refs, 'unsupported_forms': gaps,
            'macro_environment': 'NATIVE_IMAGE_EXPANDERS_OBSERVED_NOT_QUALIFIED_FOR_FULL_TARGET',
            'graph_replacement': 'NONE', 'census_acceptance': 'BLOCKED'}


def check_projection(facts, capture):
    # Compare complete records (including surplus records), with a distinct
    # direct reconstruction from each source observation rather than counts.
    require(facts['version'] == 1 and facts['status'] == 'PARTIAL_SOURCE_FACTS' and
            facts['source'] == capture['source'] and facts['source_sha256'] == SOURCE_SHA256 and
            facts['namespace'] == 'dumplisp-target-traversal', 'FACT_PROFILE')
    require(facts['graph_replacement'] == 'NONE' and facts['census_acceptance'] == 'BLOCKED' and
            facts['macro_environment'] == 'NATIVE_IMAGE_EXPANDERS_OBSERVED_NOT_QUALIFIED_FOR_FULL_TARGET', 'QUALIFICATION')
    expected_functions, expected_calls, expected_refs, expected_gaps = [], [], [], []
    for row in capture['rows']:
        if row['status'] == 'UNSUPPORTED':
            expected_gaps.append({'form': row['ordinal'], 'source_name': capture['index'][row['ordinal']-1]['name'], **row['problem']})
        todo = [row['function']] if row['function'] else []
        while todo:
            f = todo.pop(0); todo[0:0] = f['inner_functions']
            expected_functions.append(dict(id=f['function_id'], parent=f['parent_id'], name=f['name'],
                                           form=row['ordinal'], start=row['start'], end=row['end'],
                                           operators=f['operators'], variables=f['variables'],
                                           prior_unresolved_forms=row['prior_unresolved_forms']))
            for source, dest in [('calls', expected_calls), ('function_references', expected_refs)]:
                dest.extend(dict(function=f['function_id'], form=row['ordinal'], site=s['site_id'],
                                 record=s, qualification='UNQUALIFIED_TARGET_DEPENDENCY') for s in f[source])
    for field, expected in [('definitions', expected_functions), ('calls', expected_calls),
                            ('function_references', expected_refs), ('unsupported_forms', expected_gaps)]:
        require(facts[field] == expected, 'FACT_RECORDS_' + field.upper())
    require(set(facts) == {'version', 'status', 'source', 'source_sha256', 'namespace', 'definitions', 'calls',
                          'function_references', 'unsupported_forms', 'macro_environment', 'graph_replacement',
                          'census_acceptance'}, 'SURPLUS_FACT_FIELD')
