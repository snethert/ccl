"""Check one exact source replacement and its independent loader-input oracle."""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('source_boundary', HERE.parent/'source-traversal/check.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require = base.require


def read(path):
    data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return json.loads(data)


def expected_cases():
    original = 'bundle:/bootstrap/ccl.image'
    retry = 'bundle:/retry'
    def row(name, values=None, error=None, ready=False, stored=None):
        return dict(name=name, status='ERROR' if error else 'RETURNED', values=[] if error else values,
                    error=error, error_type='COMMON-LISP::SIMPLE-ERROR' if error else None,
                    ready=ready, stored=stored)
    result = [row('before-install', error='KERNEL-RESOURCE-NOT-INSTALLED')]
    result.append(row('install', [len(original)], ready=True, stored=original))
    for name in ('lookup', 'caller-input-mutated', 'returned-string-mutated'):
        result.append(row(name, [original], ready=True, stored=original))
    result.append(row('second-install', error='KERNEL-RESOURCE-ALREADY-INSTALLED', ready=True, stored=original))
    result.append(row('after-second-install', [original], ready=True, stored=original))
    for name in ('invalid-number', 'invalid-empty', 'invalid-nul'):
        result.append(row(name, error='INVALID-KERNEL-RESOURCE'))
        result.append(row(name+'-retry', [retry], ready=True, stored=retry))
    result.append(row('opaque-unicode-name', ['bundle:/a/../λ image'], ready=True, stored='bundle:/a/../λ image'))
    return result


def check(c, service_text=None):
    contract = read(HERE/'contract.json')
    original = contract['original']
    text = (ROOT/original['path']).read_text()
    require(hashlib.sha256(text.encode()).hexdigest() == original['sha256'], 'U1_SOURCE_PIN')
    require(c['version'] == 1 and c['contract'] == contract['id'] and
            c['target_runtime_implemented'] is False and c['native_reference_only'] is True, 'SCOPE')
    require(c['state_restored'] is True and c['source_bindings_unchanged'] is True, 'RESTORATION')
    base.context(c['target'])
    entry = dict(ordinal=12, start=12716, end=13142, operator='COMMON-LISP::DEFUN', name='CCL::KERNEL-PATH')
    require(c['source'] == dict(path=original['path'], entry=entry, text=text[12716:13142]), 'SOURCE_SPAN')
    old, new = c['original'], c['replacement']
    require(all(old[k] == entry[k] for k in ('ordinal','start','end','operator','name')), 'ORIGINAL_IDENTITY')
    require(old['status'] == 'UNSUPPORTED' and old['function'] is None and old['problem']['stage'] == 'front-end'
            and original['first_gap'] in old['problem']['message'], 'ORIGINAL_GAP_RETAINED')
    expected_text = (HERE/'replacement.lisp').read_text()
    require(c['replacement_text'] == expected_text and new['start'] == 0 and new['end'] == len(expected_text.rstrip())
            and new['ordinal'] == 1 and new['name'] == 'CCL::KERNEL-PATH'
            and new['operator'] == 'COMMON-LISP::DEFUN', 'REPLACEMENT_SOURCE')
    require(new['status'] == 'CAPTURED' and new['problem'] is None, 'TARGET_CAPTURE')
    for row in (old, new):
        base.context(row['reader_context'])
        require(row['prior_unresolved_forms'] == [], 'SEPARATE_SOURCE_SLICES')
    f = new['function']
    require(f['name'] == 'CCL::KERNEL-PATH' and f['inner_functions'] == [] and f['variables'] == []
            and f['function_references'] == [] and f['parent_id'] is None, 'TARGET_FUNCTION')
    require(len(f['calls']) == 1 and f['calls'][0]['operator'] == 'CCL::CALL'
            and f['calls'][0]['target'] == contract['replacement']['dependency']
            and f['calls'][0]['dependency'] == dict(category='global-binding', targets=[dict(kind='global-binding', name=contract['replacement']['dependency'])]), 'TARGET_CALL')
    # The body is a direct call, but FCOMP still expands its DEFUN wrapper.
    # Keep the native expander's identity explicit; this slice does not claim
    # full source routing or qualification of the original function's macros.
    require(new['macro_expansions'] == [dict(operator='COMMON-LISP::DEFUN',
            backend='KEYWORD::WASM32-CENSUS', source='ccl:lib;macros.lisp.newest',
            position=29147)], 'REPLACEMENT_MACRO_SCOPE')
    require(c['service_text'] == (service_text if service_text is not None else (HERE/'service.lisp').read_text()), 'REFERENCE_SOURCE')
    wanted = expected_cases()
    require(len(c['reference_cases']) == len(wanted), 'CASE_BOUND')
    for row, expected in zip(c['reference_cases'], wanted):
        require(row == expected, 'REFERENCE_CASE '+expected['name'])
    return dict(original_native_gap_preserved=True, source_replacements_captured=1,
                target_calls=1, reference_cases=len(wanted), target_runtime_implemented=False)


def joins(c):
    contract = read(HERE/'contract.json')
    f = c['replacement']['function']
    return dict(version=1, kind='SOURCE_BOUNDARY_REPLACEMENT_WITNESS', contract=contract['id'],
                original=contract['original'], replacement=dict(path=contract['replacement']['path'],
                sha256=hashlib.sha256(c['replacement_text'].encode()).hexdigest(), prototype=f['function_id']),
                edges=[dict(source_prototype=f['function_id'], site_id=f['calls'][0]['site_id'],
                target_global=contract['replacement']['dependency'], phase='compile', origin='observed-target-front-end')],
                execution_scope='NATIVE_REFERENCE_ONLY', remaining=contract['remaining'],
                complete_census_graph_modified=False)


def controls(c):
    changes = [
      ('scope-promotion', 'SCOPE', lambda x:x.update(target_runtime_implemented=True)),
      ('reference-hidden', 'SCOPE', lambda x:x.update(native_reference_only=False)),
      ('restoration-missing', 'RESTORATION', lambda x:x.update(state_restored=False)),
      ('source-offset', 'SOURCE_SPAN', lambda x:x['source']['entry'].update(start=12717)),
      ('source-body', 'SOURCE_SPAN', lambda x:x['source'].update(text='(defun kernel-path () nil)')),
      ('gap-erased', 'ORIGINAL_GAP_RETAINED', lambda x:x['original'].update(status='CAPTURED')),
      ('replacement-relabelled', 'REPLACEMENT_SOURCE', lambda x:x['replacement'].update(name='CCL::OTHER')),
      ('replacement-source', 'REPLACEMENT_SOURCE', lambda x:x.update(replacement_text='(defun kernel-path () nil)')),
      ('target-body-missing', 'TARGET_CAPTURE', lambda x:x['replacement'].update(status='UNSUPPORTED')),
      ('target-function-name', 'TARGET_FUNCTION', lambda x:x['replacement']['function'].update(name='CCL::OTHER')),
      ('service-call-omitted', 'TARGET_CALL', lambda x:x['replacement']['function'].update(calls=[])),
      ('service-call-added', 'TARGET_CALL', lambda x:x['replacement']['function']['calls'].append(deepcopy(x['replacement']['function']['calls'][0]))),
      ('native-call-substituted', 'TARGET_CALL', lambda x:x['replacement']['function']['calls'][0].update(target='CCL::%GET-KERNEL-GLOBAL-PTR')),
      ('macro-context-substituted', 'REPLACEMENT_MACRO_SCOPE', lambda x:x['replacement']['macro_expansions'][0].update(backend='KEYWORD::DARWINX8664')),
      ('service-body-unbound', 'REFERENCE_SOURCE', lambda x:x.update(service_text='')),
      ('case-omitted', 'CASE_BOUND', lambda x:x['reference_cases'].pop()),
      ('case-duplicated', 'CASE_BOUND', lambda x:x['reference_cases'].append(deepcopy(x['reference_cases'][0]))),
      ('failure-state-promoted', 'REFERENCE_CASE invalid-number', lambda x:x['reference_cases'][7].update(ready=True)),
      ('native-name-substituted', 'REFERENCE_CASE lookup', lambda x:x['reference_cases'][2].update(values=['/native/kernel'])),
    ]
    results = []
    for name, reason, mutate in changes:
        changed = deepcopy(c)
        mutate(changed)
        try:
            check(changed)
        except ValueError as e:
            require(str(e) == reason, 'CONTROL_REASON '+name+': '+str(e))
        else:
            raise ValueError('CONTROL_ESCAPED '+name)
        results.append(dict(name=name, status='REJECTED', reason=reason))
    return results
