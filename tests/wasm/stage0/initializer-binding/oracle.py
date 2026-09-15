"""Independent expectations for S0-LL15-a initializer binding.

check() takes the observations of every case (complete first, then the
controls in CASES order) and raises ValueError naming the first failing
check, or returns a summary. The expected memory image of each case is
reconstructed here from the manifest, the interface and the case's declared
effects, then compared with the retained snapshot byte for byte.
"""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABI = json.loads((HERE / 'abi.json').read_text())
CLOSURE = json.loads((HERE / 'closure.json').read_text())
R = ABI['regions']
INIT = {i['id']: i for i in CLOSURE['initializers']}
ORDER = ['init_map', 'init_diagnostics', 'init_install', 'init_symbols', 'init_readers', 'init_errors', 'init_compiler', 'activate_errors', 'finalize']
COMPLETION = [INIT[i]['completion'] for i in sorted(INIT, key=lambda k: INIT[k]['ordinal'])]
CHECKSUM = 0
for c in COMPLETION:
    CHECKSUM ^= c
SUMMARY = sum(COMPLETION[:8])
MEMORY_BYTES = ABI['memory']['pages'] * 65536
# Word effects of each genuine initializer, in execution order; complete() adds the ledger writes.
EFFECTS = {
    'init_map': [(2048, 3), (2052, 1024), (2056, 1312), (2060, 1), (2064, 4096), (2068, 8192), (2072, 2), (2076, 8192), (2080, 12288), (2084, 3), (77824, 77825), (77828, 77825), (77832, 1850)],
    'init_diagnostics': [(1280, 1), (1284, 53670)],
    'init_install': [(1288, 4)],
    'init_symbols': [(8192, 4), (8196, 1850), (8200, 1850), (8204, 1850), (8208, 1850)],
    'init_readers': [(8448, 2), (8452, 8196), (8456, 8200)],
    'init_errors': [(8704, 3), (8708, 8196), (8712, 8200), (8716, 8204)],
    'init_compiler': [(8960, 2), (8964, 8708), (8968, 8712)],
    'activate_errors': [(1280, 2)],
    'finalize': [(1292, SUMMARY)],
}
MODULE_INDEX = {name: k for k, name in enumerate(CLOSURE['modules'])}
# case -> (expected result, initializers that ran, extra word effects of the control module, events after the last genuine step)
# result: ('ready',) or ('refusal', reason, stage)
CASES = {
    'complete': dict(result=('ready',), ran=ORDER, partial=[], tail=[700]),
    'omitted-module': dict(result=('refusal', 'REQUIRED_MODULE_OMITTED bundle-b', 'modules'), ran=[], partial=[], tail=[], no_core=True),
    'no-export': dict(result=('refusal', 'MISSING_INITIALIZER_EXPORT bundle-b.init_errors', 'modules'), ran=[], partial=[], tail=[], no_core=True),
    'import-mismatch': dict(result=('refusal', 'IMPORT_MISMATCH bundle-a', 'modules'), ran=[], partial=[], tail=[], no_core=True),
    'deferred-required': dict(result=('refusal', 'DEFERRED_REQUIRED_MODULE bundle-c', 'manifest'), ran=[], partial=[], tail=[], no_core=True),
    'unknown-prerequisite': dict(result=('refusal', 'UNKNOWN_PREREQUISITE init_compiler -> init_ffi', 'manifest'), ran=[], partial=[], tail=[], no_core=True),
    'cycle': dict(result=('refusal', 'INITIALIZATION_CYCLE init_readers,init_symbols', 'manifest'), ran=[], partial=[], tail=[], no_core=True),
    'forward-phase': dict(result=('refusal', 'FORWARD_PHASE_DEPENDENCY init_compiler -> activate_errors', 'manifest'), ran=[], partial=[], tail=[], no_core=True),
    'loader-unseeded': dict(result=('refusal', 'LOADER_DEPENDENCY_NOT_SEEDED init_install', 'manifest'), ran=[], partial=[], tail=[], no_core=True),
    'bundle-in-loader-phase': dict(result=('refusal', 'BUNDLE_IN_LOADER_PHASE bundle-a', 'manifest'), ran=[], partial=[], tail=[], no_core=True),
    'wrong-completion': dict(result=('refusal', 'COMPLETION_MISMATCH init_errors', 'completion'), ran=ORDER[:5], attempted='init_errors', partial=[(8704, 3), (1044, 1), (1172, 1)], tail=[800]),
    'returns-only': dict(result=('refusal', 'COMPLETION_NOT_WRITTEN init_errors', 'completion'), ran=ORDER[:5], attempted='init_errors', partial=[], tail=[800]),
    'throws': dict(result=('refusal', 'INITIALIZER_FAILED init_errors', 'run'), ran=ORDER[:5], attempted='init_errors', partial=[(8704, 3)], tail=[800]),
    'clobbered-prerequisite': dict(result=('refusal', 'COMPLETION_MISMATCH activate_errors <- init_errors', 'prerequisites'), ran=ORDER[:7], partial=[(1044, 7)], tail=[800]),
    'state-mismatch': dict(result=('refusal', 'STATE_MISMATCH finalize @1280', 'prerequisites'), ran=ORDER[:8], partial=[], tail=[800]),
}


def require(condition, name):
    if not condition:
        raise ValueError(name)


def background():
    image = bytearray(MEMORY_BYTES)
    for i in range(MEMORY_BYTES):
        image[i] = (i * 13 + 7) % 256
    return image


def store(image, address, value):
    image[address:address + 4] = (value & 0xffffffff).to_bytes(4, 'little')


def expected_image(case):
    spec = CASES[case]
    image = background()
    for base, count in ((R['completion_words']['base'], 16), (R['execution_counters']['base'], 16)):
        for k in range(count):
            store(image, base + 4 * k, 0)
    for a in (R['mode_word'], R['fatal_sink'], R['slot_count'], R['summary_word'], R['ready']['generation'], R['ready']['count'], R['ready']['checksum'], R['event_log']['count']):
        store(image, a, 0)
    events = []
    if not spec.get('no_core'):
        events.append(500 + MODULE_INDEX['loader-core'])
        loaded_bundles = False
        for ident in spec['ran'] + ([spec['attempted']] if spec.get('attempted') else []):
            i = INIT[ident]
            if i['phase'] != 0 and not loaded_bundles:
                events += [500 + MODULE_INDEX[m] for m in CLOSURE['modules'] if CLOSURE['modules'][m]['role'] != 'loader']
                loaded_bundles = True
            events += [200 + i['ordinal'], 300 + i['ordinal'], 100 + i['ordinal']]
            if ident in spec['ran']:
                for address, value in EFFECTS[ident]:
                    store(image, address, value)
                store(image, R['completion_words']['base'] + 4 * i['ordinal'], i['completion'])
                store(image, R['execution_counters']['base'] + 4 * i['ordinal'], 1)
                events.append(400 + i['ordinal'])
        for address, value in spec['partial']:
            store(image, address, value)
        if spec['result'][0] == 'ready':
            store(image, R['ready']['generation'], 1); store(image, R['ready']['count'], len(ORDER)); store(image, R['ready']['checksum'], CHECKSUM)
        events += spec['tail']
        store(image, R['event_log']['count'], len(events))
        for k, code in enumerate(events):
            store(image, R['event_log']['base'] + 4 * k, code)
    return image, events


def check(observations, snapshots):
    """observations: {case: observed dict}; snapshots: {case: gzipped memory bytes}."""
    require(list(observations) == list(CASES), 'CASE inventory')
    for case, spec in CASES.items():
        o = observations[case]; result = o.get('result') or {}
        require('crash' not in result, 'RESULT ' + case + ' crashed')
        if spec['result'][0] == 'ready':
            require(result.get('ready') == {'generation': 1, 'count': len(ORDER), 'checksum': CHECKSUM, 'order': ORDER}, 'RESULT ' + case)
            require([l['id'] for l in result.get('ledger', [])] == ORDER and all(l['completion'] == INIT[l['id']]['completion'] and l['counter'] == 1 for l in result['ledger']), 'LEDGER ' + case)
        else:
            refusal = result.get('refusal') or {}
            require(refusal.get('reason') == spec['result'][1] and refusal.get('stage') == spec['result'][2], 'RESULT ' + case + ' ' + str(refusal.get('reason')))
            expected_ran = spec['ran'] + ([spec['attempted']] if spec.get('attempted') and spec['result'][2] == 'completion' else [])
            require(refusal.get('ran') == expected_ran, 'RAN ' + case)
            require('ready' not in result, 'READY ' + case + ' published after refusal')
        p = o.get('physical') or {}
        expected_words = [0] * 16
        for ident in spec['ran']:
            expected_words[INIT[ident]['ordinal']] = INIT[ident]['completion']
        for address, value in spec['partial']:
            if R['completion_words']['base'] <= address < R['completion_words']['base'] + 64:
                expected_words[(address - R['completion_words']['base']) // 4] = value
        require(p.get('completion_words') == expected_words, 'PHYSICAL ' + case + ' completion words')
        expected_counters = [0] * 16
        for ident in spec['ran']:
            expected_counters[INIT[ident]['ordinal']] = 1
        for address, value in spec['partial']:
            if R['execution_counters']['base'] <= address < R['execution_counters']['base'] + 64:
                expected_counters[(address - R['execution_counters']['base']) // 4] = value
        require(p.get('execution_counters') == expected_counters, 'PHYSICAL ' + case + ' counters')
        if spec['result'][0] == 'ready':
            require(p.get('mode') == 2 and p.get('fatal_sink') == 53670 and p.get('slot_count') == 4 and p.get('summary') == SUMMARY, 'PHYSICAL ' + case + ' services')
            require(p.get('ready') == {'generation': 1, 'count': len(ORDER), 'checksum': CHECKSUM}, 'PHYSICAL ' + case + ' ready')
            require(p.get('canonical') == {'nil_cdr': 77825, 'nil_car': 77825, 't_header': 1850}, 'PHYSICAL ' + case + ' canonical')
            require(p['definitions']['symbol_table'][:5] == [4, 1850, 1850, 1850, 1850] and p['definitions']['handler_table'][:4] == [3, 8196, 8200, 8204], 'PHYSICAL ' + case + ' definitions')
        else:
            require(p.get('ready') == {'generation': 0, 'count': 0, 'checksum': 0}, 'PHYSICAL ' + case + ' ready withheld')
        image, events = expected_image(case)
        require(p.get('event_log') == events, 'EVENTS ' + case)
        require(result.get('events') == ([e for e in events if e // 100 != 1 and e // 100 != 9] if not spec.get('no_core') else [800]), 'EVENTS ' + case + ' loader ledger')
        require(gzip.decompress(snapshots[case]) == bytes(image), 'IMAGE ' + case)
    return {'cases': len(CASES), 'initializers': len(ORDER), 'phases': len(CLOSURE['phases']), 'checksum': CHECKSUM, 'summary': SUMMARY}
