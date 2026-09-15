"""Independent expectations for S0-LL21-c materialization observations.

check() raises ValueError naming the first failing check, or returns the
summary row. Expected values derive from abi.json and the fixture contract,
never from an engine's output.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABI = json.loads((HERE / 'abi.json').read_text())
TEMPLATE_FEATURES = ['atomics', 'multivalue', 'tailcall']
RESULTS = [[43, 2], [44, 2]]
CONTROLS = [
    ('wrong-offset', 'wrong structural offset'),
    ('wrong-original-byte', 'wrong original limits byte'),
    ('wrong-template-hash', 'template hash mismatch'),
    ('tampered-template', 'template hash mismatch'),
    ('wrong-maximum', 'wrong structural maximum'),
    ('import-mismatch', 'import inventory mismatch'),
    ('export-mismatch', 'export inventory mismatch'),
    ('feature-mismatch', 'feature requirement mismatch'),
    ('stale-materializer-version', 'unsupported materialization contract'),
    ('unknown-profile', 'unknown profile'),
    ('profile-not-admitted', 'profile not admitted on the target engine'),
    ('already-shared-template', 'template already declares shared memory'),
    ('defined-memory-template', 'template must import env.memory'),
    ('unbounded-template', 'requires canonical unshared explicit-maximum memory'),
    ('wait-in-template', 'template contains wait or notify instructions'),
    ('wrong-signature-template', 'exports differ from the interface'),
    ('stale-binary-hash', 'installed binary hash mismatch'),
    ('template-hash-as-identity', 'template hash is not an installed-binary identity'),
    ('stale-install-version', 'stale materializer version'),
    ('runtime-profile-mismatch', 'runtime carries a wait path the profile prohibits'),
    ('runtime-unshared-wait', 'runtime carries a wait path the profile prohibits'),
    ('runtime-without-wait-for-full', 'full-profile runtime lacks its wait path'),
    ('runtime-shared-memory-for-unshared-profile', 'runtime memory declaration does not match the profile'),
]


def require(condition, name):
    if not condition:
        raise ValueError(name)


def value(record, name):
    require(isinstance(record, dict) and 'value' in record and 'error' not in record, name)
    return record['value']


def error_class(record, name):
    require(isinstance(record, dict) and isinstance(record.get('error'), str), name)
    return record['error']


def check(observed):
    require(isinstance(observed, dict), 'OBSERVED')
    require(observed.get('materializer_version') == ABI['materializer_version'], 'MATERIALIZER version')
    m = observed.get('manifest') or {}
    require(m.get('version') == ABI['materializer_version'] and m.get('materializer_version') == ABI['materializer_version'], 'MANIFEST version')
    require(m.get('original_byte') == 1 and m.get('minimum') == ABI['template']['memory']['minimum'] and m.get('maximum') == ABI['template']['memory']['maximum'], 'MANIFEST limits')
    require(m.get('imports') == ABI['template']['function_imports'], 'MANIFEST imports')
    require(m.get('exports') == ABI['template']['exports'], 'MANIFEST exports')
    require(m.get('features') == TEMPLATE_FEATURES, 'MANIFEST features')
    require(isinstance(m.get('offset'), int) and m['offset'] > 8, 'MANIFEST offset')
    mat = observed.get('materialized') or {}
    shared, unshared, callback = mat.get('shared') or {}, mat.get('unshared') or {}, mat.get('callback') or {}
    require(shared.get('profile') == 'full' and shared.get('shared') is True and shared.get('patched_byte') == 3, 'MATERIALIZED shared')
    require(unshared.get('profile') == 'single_thread_jspi' and unshared.get('shared') is False and unshared.get('patched_byte') == 1, 'MATERIALIZED unshared')
    require(callback.get('profile') == 'precompiled_callback' and callback.get('shared') is False, 'MATERIALIZED callback')
    for r in (shared, unshared, callback):
        require(r.get('template_sha256') == m.get('template_sha256') and r.get('offset') == m['offset'] and r.get('features') == TEMPLATE_FEATURES, 'MATERIALIZED record')
        require(r.get('limits') == {'minimum': m['minimum'], 'maximum': m['maximum']} and r.get('bytes') == shared.get('bytes'), 'MATERIALIZED limits')
    require(shared.get('binary_sha256') != m.get('template_sha256'), 'MATERIALIZED shared identity')
    require(unshared.get('binary_sha256') == m.get('template_sha256') == callback.get('binary_sha256'), 'MATERIALIZED unshared identity')
    d = observed.get('byte_difference') or {}
    require(d.get('length_preserved') is True and d.get('unshared_identical') is True and d.get('callback_identical') is True, 'BYTES preserved')
    require(d.get('differences') == [{'offset': m['offset'], 'template': 1, 'shared': 3}], 'BYTES single flag')
    lim = observed.get('import_limits') or {}
    for name in ('unshared_matching', 'unshared_larger_minimum', 'unshared_smaller_maximum', 'shared_matching'):
        require(value(lim.get(name), 'LIMITS ' + name) == 'linked', 'LIMITS ' + name)
    for name in ('unshared_larger_maximum', 'unshared_unbounded', 'unshared_with_shared_memory', 'shared_larger_maximum', 'shared_with_unshared_memory'):
        require(error_class(lim.get(name), 'LIMITS ' + name) == 'LinkError', 'LIMITS ' + name)
    for profile in ('unshared', 'shared'):
        g = (observed.get('growth') or {}).get(profile) or {}
        require(g == {'to_maximum': 1, 'beyond_maximum': -1, 'size': 4, 'buffer_bytes': 262144}, 'GROWTH ' + profile)
    inst = observed.get('installation') or {}
    require(value(inst.get('shared'), 'INSTALL shared') == 'installed' and value(inst.get('unshared'), 'INSTALL unshared') == 'installed', 'INSTALL')
    rc = observed.get('runtime_checks') or {}
    require(value(rc.get('full'), 'RUNTIME full') == {'memory': {'flags': 3, 'minimum': 1, 'maximum': 4}, 'function_imports': []}, 'RUNTIME full')
    require(value(rc.get('jspi'), 'RUNTIME jspi') == {'memory': {'flags': 1, 'minimum': 1, 'maximum': 4}, 'function_imports': ['host.io']}, 'RUNTIME jspi')
    require(value(rc.get('sync'), 'RUNTIME sync') == {'memory': {'flags': 1, 'minimum': 1, 'maximum': 4}, 'function_imports': []}, 'RUNTIME sync')
    p = observed.get('profiles') or {}
    full = p.get('full') or {}
    require(full.get('served') == [{'argument': 21, 'answer': 42, 'woken': 1}] * 2, 'FULL served')
    require((full.get('worker') or {}).get('status') == 'OK', 'FULL worker')
    require(full['worker'].get('results') == RESULTS, 'FULL results')
    require(full['worker'].get('size') == 1 and full.get('counter') == 2, 'FULL counter')
    jspi = p.get('single_thread_jspi') or {}
    require(jspi.get('available') is True, 'JSPI available')
    require(jspi.get('results') == RESULTS, 'JSPI results')
    require(jspi.get('suspensions') == 2 and jspi.get('counter') == 2, 'JSPI suspensions')
    cb = p.get('precompiled_callback') or {}
    require(cb.get('results') == RESULTS and cb.get('counter') == 2, 'CALLBACK results')
    controls = observed.get('controls') or {}
    for name, reason in CONTROLS:
        require(controls.get(name) == {'refused': reason}, 'CONTROL ' + name)
    require(error_class(controls.get('runtime-unshared-wait-execution'), 'CONTROL execution witness') == 'RuntimeError', 'CONTROL execution witness')
    require(set(controls) == {n for n, _ in CONTROLS} | {'runtime-unshared-wait-execution'}, 'CONTROL inventory')
    return {'template_sha256': m['template_sha256'], 'shared_binary_sha256': shared['binary_sha256'], 'unshared_binary_sha256': unshared['binary_sha256'],
            'flag_offset': m['offset'], 'features': TEMPLATE_FEATURES, 'profiles': ['full', 'single_thread_jspi', 'precompiled_callback'], 'controls': len(CONTROLS) + 1}
