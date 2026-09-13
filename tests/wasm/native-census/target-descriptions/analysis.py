"""Check the scoped description extension; do not grant census acceptance."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('reviewed_source_check', HERE.parent/'source-traversal/check.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require = base.require
functions = base.functions

LAYOUT = [('basic-stream', 'basic-stream', 6, 2), ('instance', 'instance', 14, 2),
          ('struct', 'struct', 15, 2), ('istruct', 'istruct', 16, 2),
          ('min-cl-ivector-subtag', 'single-float-vector', 19, 7),
          ('array-header', 'arrayH', 29, 2), ('vector-header', 'vectorH', 30, 2),
          ('simple-vector', 'simple-vector', 31, 2)]
GAPS = {k: v for k, v in base.FAILURES.items() if k in (9, 10, 11, 12, 13)}
NATIVE_CONTROLS = {'omit-types': 'TYPE_DESCRIPTIONS', 'omit-batch-macro': 'BODY_CAPTURE',
                   'erase-batch-dependency': 'BATCH_DEPENDENCY', 'first-capture': 'DEFINITION_IDENTITY',
                   'execute-initializer': 'BODY_CAPTURE', 'alias-initializers': 'INITIALIZER_BIJECTION'}
CONTRACTS = [('STARTUP-BATCH-FLAG', 15), ('KERNEL-RESOURCE-IDENTITY', 12),
             ('IMAGE-SAVE-EXIT', 9), ('NATIVE-EMBEDDED-IMAGE', 10),
             ('NATIVE-EXECUTABLE-PREFIX', 11), ('IMAGE-BUNDLE-WRITER', 13),
             ('DECLARED-ENTRYPOINT-RESTORE', 15), ('CALLBACK-REGISTRY-RESTORE', 16)]


def check_descriptions(d, root=ROOT):
    for path, digest in d['source_sha256'].items():
        require(hashlib.sha256((root/path).read_bytes()).hexdigest() == digest, 'DESCRIPTION_SOURCE')
    source = (root/'compiler/X86/X8632/x8632-arch.lisp').read_text()
    require('(logior ,tag (ash ,subtag ntagbits))' in source, 'SUBTAG_FORMULA')
    for name, value in [('ntagbits', 3), ('fulltag-nodeheader', 2), ('fulltag-immheader', 7)]:
        require(re.search(r'\(defconstant\s+'+name+r'\s+'+str(value)+r'\)', source), 'SUBTAG_BASE')
    require(len(d['layout']) == len(LAYOUT), 'LAYOUT_COUNT')
    for record, (key, name, index, tag) in zip(d['layout'], LAYOUT):
        kind = 'node' if tag == 2 else 'imm'
        require(re.findall(r'\(define-'+kind+r'-subtag\s+'+re.escape(name)+r'\s+(\d+)\)', source) == [str(index)], 'SUBTAG_SOURCE')
        constant = 'MIN-CL-IVECTOR-SUBTAG' if key == 'min-cl-ivector-subtag' else 'SUBTAG-'+name.upper()
        require(record == dict(keyword=key, source_name=name, source_index=index, fulltag=tag,
                               subtag=(index << 3) | tag, constant=constant,
                               scope='type-classification metadata; payload layout/GC qualification outstanding'), 'LAYOUT_RECORD')
    require('(defconstant min-cl-ivector-subtag subtag-single-float-vector)' in source, 'VECTOR_LOWER_BOUND')
    require([(r['id'], r['source_form']) for r in d['contracts']] == CONTRACTS, 'CONTRACT_INVENTORY')
    for r in d['contracts']:
        require('CCL::'+r['source_function'] == base.NAMES[r['source_form']-1], 'CONTRACT_SOURCE')
        require(r['disposition'] == 'REPLACEMENT_REQUIRED' and r['implementation'] == 'ABSENT'
                and r['condition_test'] == 'NOT_RUN', 'CONTRACT_DISPOSITION')


def targets(f):
    return [t['name'] for child in functions(f) for c in child['calls']
            for t in c['dependency']['targets'] if t['kind'] == 'global-binding']


def check_capture(c, source, d):
    require(hashlib.sha256(source).hexdigest() == base.SOURCE_SHA256, 'SOURCE_IDENTITY')
    text = source.decode('ascii')
    require(c['version'] == 1 and c['source'] == 'lib/dumplisp.lisp', 'PROFILE')
    require(c['eof'] == c['characters'] == len(text) and c['tail_start'] == base.ENDS[-1]
            and not text[c['tail_start']:].strip(), 'SOURCE_EOF')
    for k in ('native_state_restored', 'source_bindings_unchanged', 'description_state_restored',
              'nonlocal_description_state_restored'):
        require(c[k] is True, 'RESTORATION')
    base.context(c['target'])
    require(c['types'] == [dict(name='KEYWORD::'+k.upper(), subtag=(n << 3) | tag)
                           for k, _, n, tag in LAYOUT], 'TYPE_DESCRIPTIONS')
    require(c['constants'] == [dict(name=r['constant'], value=r['subtag']) for r in d['layout']], 'TARGET_CONSTANTS')
    index, rows = c['index'], c['rows']
    require(len(rows) == len(index) == 16, 'FORM_COVERAGE')
    require([r['name'] for r in index] == base.NAMES and [r['operator'] for r in index] == base.OPERATORS
            and [r['end'] for r in index] == base.ENDS, 'SOURCE_INVENTORY')
    prior, fs, function_forms = [], [], {}
    for ordinal, (entry, row) in enumerate(zip(index, rows), 1):
        start = 0 if ordinal == 1 else base.ENDS[ordinal-2]
        require(entry['ordinal'] == row['ordinal'] == ordinal and entry['start'] == row['start'] == start
                and row['end'] == entry['end'], 'FORM_RANGES')
        base.context(row['reader_context'])
        require(row['prior_unresolved_forms'] == prior, 'PRIOR_GAPS')
        if ordinal in GAPS:
            stage, marker = GAPS[ordinal]
            require(row['status'] == 'UNSUPPORTED' and row['function'] is None and row['problem']
                    and row['problem']['stage'] == stage and marker in row['problem']['message'], 'BOUNDARY_GAP')
            prior.append(ordinal)
            if stage == 'read':
                require(row['name'] is None and row['operator'] is None, 'FAILED_READ_PROMOTION')
                continue
        elif ordinal in (2, 3):
            require(row['status'] == 'TOPLEVEL-PROCESSED' and row['function'] is None
                    and row['deferred_output_opcodes'] and row['problem'] is None, 'DECLARATION')
        else:
            require(row['status'] == 'CAPTURED' and row['function'] and row['problem'] is None, 'BODY_CAPTURE')
            require(row['function']['name'] == (entry['name'] or 'NIL'), 'DEFINITION_IDENTITY')
            for f in functions(row['function']):
                fs.append(f); function_forms[f['function_id']] = ordinal
        require(row['name'] == entry['name'] and row['operator'] == entry['operator'], 'TARGET_FORM')
        require(any(m['operator'] == entry['operator'] and m['backend'] == 'KEYWORD::WASM32-CENSUS'
                    for m in row['macro_expansions']), 'MACRO_WITNESS')
    # Named calls independently read from the U1 source; an empty marker is not enough.
    restore = rows[14]['function']
    require(targets(restore).count('WASM-CENSUS-SERVICES::STARTUP-BATCH-FLAG') == 1, 'BATCH_DEPENDENCY')
    require(c['expansions'] == [dict(source="(CCL::%GET-KERNEL-GLOBAL 'CCL::BATCH-FLAG)",
                                   contract='STARTUP-BATCH-FLAG', expansion='(WASM-CENSUS-SERVICES::STARTUP-BATCH-FLAG)',
                                   implementation='REPLACEMENT_REQUIRED')], 'BATCH_EXPANSION')
    for ordinal, names in [(5, ['CCL::CLEAR-OPEN-FILE-STREAMS']),
                           (6, ['CCL::%MAP-AREAS', 'CCL::SLOT-ID-BOUNDP']),
                           (14, ['CCL::%%SAVE-APPLICATION']),
                           (15, ['CCL::%REVIVE-SYSTEM-LOCKS', 'CCL::REFRESH-EXTERNAL-ENTRYPOINTS',
                                 'CCL::RESTORE-PASCAL-FUNCTIONS', 'CCL::INITIALIZE-INTERACTIVE-STREAMS']),
                           (16, ['CCL::RESET-CALLBACK-STORAGE', 'CCL::%REVIVE-MACPTR', 'CCL::MAKE-CALLBACK-TRAMPOLINE'])]:
        require(set(names) <= set(targets(rows[ordinal-1]['function'])), 'SOURCE_CALLS')
    initializers, links = c['load_time_initializers'], c['load_time_links']
    require(len(initializers) == len(links) == 4, 'INITIALIZER_COVERAGE')
    wanted = Counter({'CCL::FIND-CLASS-CELL': 1, 'CCL::ENSURE-SLOT-ID': 3})
    require(Counter(t for i in initializers for t in targets(i['function'])) == wanted, 'INITIALIZER_CALLS')
    for i in initializers:
        require(i['deferred_token_matches'] is True and i['executed'] is False, 'INITIALIZER_EXECUTION')
        require(function_forms.get(i['owner_id']) == 6 and
                i['owner_id'] == rows[5]['function']['inner_functions'][0]['function_id'], 'INITIALIZER_OWNER')
        fs.extend(functions(i['function']))
    require(Counter((i['owner_id'], i['function']['function_id']) for i in initializers)
            == Counter((e['owner_id'], e['initializer_id']) for e in links), 'INITIALIZER_BIJECTION')
    require(len({e['site_id'] for e in links}) == 4, 'INITIALIZER_SITES')
    ids = [f['function_id'] for f in fs]
    require(len(ids) == len(set(ids)) == 22, 'FUNCTION_IDENTITIES')
    sites = [e['site_id'] for e in links]
    for f in fs:
        require(all(child['parent_id'] == f['function_id'] for child in f['inner_functions']), 'LEXICAL_PARENT')
        for call in f['calls'] + f['function_references']:
            sites.append(call['site_id'])
            for t in call['dependency']['targets']:
                require((t['kind'] == 'function' and t['id'] in ids) or
                        (t['kind'] == 'global-binding' and t['name']), 'CALL_TARGET')
    require(len(sites) == len(set(sites)), 'SITE_IDENTITIES')
    require({r['ordinal']: sum(not c['dependency']['targets'] for f in functions(r['function']) for c in f['calls'])
             for r in rows if r['function'] and any(not c['dependency']['targets']
                for f in functions(r['function']) for c in f['calls'])} == {7: 1, 8: 1, 15: 5}, 'INDIRECT_CALLS')
    return dict(top_level_forms=16, function_definitions=12, captured_definitions=7,
                unsupported_definitions=5, top_level_initializer_bodies=2, load_time_initializer_bodies=4,
                code_prototypes=len(fs), call_sites=sum(len(f['calls']) for f in fs),
                function_reference_sites=sum(len(f['function_references']) for f in fs),
                unresolved_calls=sum(not s['dependency']['targets'] for f in fs for s in f['calls']))


def project(c, d):
    return dict(version=1, status='PARTIAL_DESCRIBED_SOURCE_FACTS', source_facts=base.project(c),
                load_time_initializers=deepcopy(c['load_time_initializers']),
                load_time_links=deepcopy(c['load_time_links']), boundary_obligations=deepcopy(d['contracts']),
                subtype_descriptions=deepcopy(d['layout']), macro_environment_qualified=False,
                graph_edges_replaced=0, census_acceptance='BLOCKED')


def check_projection(f, c, d):
    base.check_projection(f['source_facts'], c)
    require(f['version'] == 1 and f['status'] == 'PARTIAL_DESCRIBED_SOURCE_FACTS' and
            f['macro_environment_qualified'] is False and f['graph_edges_replaced'] == 0 and
            f['census_acceptance'] == 'BLOCKED', 'FACT_QUALIFICATION')
    for dest, original in [('load_time_initializers', c['load_time_initializers']),
                           ('load_time_links', c['load_time_links']),
                           ('boundary_obligations', d['contracts']), ('subtype_descriptions', d['layout'])]:
        require(f[dest] == original, 'FACT_'+dest.upper())
    require(set(f) == {'version', 'status', 'source_facts', 'load_time_initializers', 'load_time_links',
                       'boundary_obligations', 'subtype_descriptions', 'macro_environment_qualified',
                       'graph_edges_replaced', 'census_acceptance'}, 'FACT_SURPLUS')
