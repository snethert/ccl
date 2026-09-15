"""Independent expectations for the S0-ENGINE-a matrix.

check() reads one engine's observed record and raises ValueError with the name
of the first failing check, or returns the matrix row for that engine. The
expected values are computed here from the fixture contract, not copied from
any engine's output.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEATURES = json.loads((HERE / 'features.json').read_text())
TAIL_DEPTH = FEATURES['tail_depth']
REQUIRED_PROBES = ['multivalue', 'tailcall', 'exceptions', 'exnref', 'bulk', 'atomics']
INFORMATIONAL_PROBES = ['legacy-eh', 'memory64']
PROBES = REQUIRED_PROBES + INFORMATIONAL_PROBES


def expected_region():
    seed = FEATURES['seed'].encode('ascii')
    assert len(seed) == 23
    region = bytearray(80)
    region[0:23] = seed          # memory.init at 128
    region[32:55] = seed         # memory.copy to 160
    region[64:72] = b'Z' * 8     # memory.fill at 192
    return region.hex()


def require(condition, name):
    if not condition:
        raise ValueError(name)


def value(record, name):
    require(isinstance(record, dict) and 'value' in record and 'error' not in record, name)
    return record['value']


def error_class(record, name):
    require(isinstance(record, dict) and isinstance(record.get('error'), str) and record['error'], name)
    return record['error']


def check_detection(observed):
    detection = observed.get('detection') or {}
    for probe in REQUIRED_PROBES:
        require(detection.get(probe) is True, 'DETECTION ' + probe)
    require(detection.get('invalid') is False, 'DETECTION invalid')
    for probe in INFORMATIONAL_PROBES:
        require(isinstance(detection.get(probe), bool), 'DETECTION recorded ' + probe)
    return {probe: detection[probe] for probe in PROBES}


def check_core(core):
    mv = core.get('multivalue') or {}
    require(value(mv.get('pair'), 'MULTIVALUE pair') == [41, 42], 'MULTIVALUE pair')
    require(value(mv.get('block_pair'), 'MULTIVALUE block') == 7, 'MULTIVALUE block')
    tail = core.get('tail') or {}
    require(tail.get('depth') == TAIL_DEPTH, 'TAIL depth')
    require(value(tail.get('direct'), 'TAIL direct') == TAIL_DEPTH, 'TAIL direct')
    require(value(tail.get('indirect'), 'TAIL indirect') == TAIL_DEPTH, 'TAIL indirect')
    eh = core.get('exceptions') or {}
    require(value(eh.get('nested'), 'EH nested') == 1234, 'EH nested')
    require(value(eh.get('passages'), 'EH passages') == 1, 'EH passages')
    require(value(eh.get('catch_all'), 'EH catch_all') == 7777, 'EH catch_all')
    uncaught = eh.get('uncaught') or {}
    require(uncaught.get('is_wasm_exception') is True and uncaught.get('is_lisp_tag') is True and uncaught.get('arg') == 31337, 'EH uncaught')
    require(value(eh.get('js_caught_by_catch_all'), 'EH js_caught') == 1, 'EH js_caught')
    require(eh.get('js_rethrown_same_object') is True, 'EH js_rethrow')
    bulk = core.get('bulk') or {}
    require(isinstance(bulk.get('call'), dict) and 'error' not in bulk['call'], 'BULK call')
    require(bulk.get('region_128_207') == expected_region(), 'BULK bytes')
    require(isinstance(bulk.get('drop'), dict) and 'error' not in bulk['drop'], 'BULK drop')
    require(error_class(bulk.get('reinit_after_drop'), 'BULK reinit') == 'RuntimeError', 'BULK reinit')


def check_growth(growth, old_bytes, name):
    require(isinstance(growth, dict), name + ' growth')
    require(growth.get('old_buffer_bytes_after_grow') == old_bytes, name + ' growth old')
    require(growth.get('new_buffer_bytes') == 131072, name + ' growth new')
    require(growth.get('old_buffer_identity_retained') is False, name + ' growth identity')
    require(value(growth.get('size_pages'), name + ' growth size') == 2, name + ' growth size')


def check_full(full, expected):
    if not expected:
        require(full.get('available') is False and isinstance(full.get('reason'), str), 'FULL unavailable')
        return {'available': False, 'reason': full['reason']}
    require(full.get('available') is True and full.get('memory') == 'shared', 'FULL available')
    require('failure' not in full, 'FULL waiter signalled')
    require(value(full.get('linked_in_main'), 'FULL linked') == 1, 'FULL linked')
    require(full.get('woken') == 1, 'FULL woken')
    waiter = full.get('waiter') or {}
    require(waiter.get('status') == 'OK', 'FULL waiter status')
    require(waiter.get('code') == 0, 'FULL wake code')
    require(waiter.get('mailbox') == 42, 'FULL mailbox')
    require(waiter.get('timed_out_code') == 2, 'FULL timed-out code')
    require(waiter.get('not_equal_code') == 1, 'FULL not-equal code')
    require(waiter.get('rmw_before') == 0 and waiter.get('rmw_after') == 5, 'FULL rmw')
    require(value(full.get('grow'), 'FULL grow') == 1, 'FULL grow')
    check_growth(full.get('growth'), 65536, 'FULL')
    return {'available': True, 'wake_code': 0, 'timed_out_code': 2, 'not_equal_code': 1, 'notified': 1}


def check_jspi(jspi, expected):
    if not expected:
        require(jspi.get('available') is False and isinstance(jspi.get('reason'), str), 'JSPI unavailable')
        return {'available': False, 'reason': jspi['reason']}
    require(jspi.get('available') is True, 'JSPI available')
    require(value(jspi.get('run'), 'JSPI run') == 105, 'JSPI run')
    require(value(jspi.get('run_tail'), 'JSPI run_tail') == 50, 'JSPI run_tail')
    require(jspi.get('suspensions') == 3, 'JSPI suspensions')
    require(error_class(jspi.get('non_promising_call'), 'JSPI non-promising') != 'RangeError', 'JSPI non-promising')
    require(jspi.get('returned_promise') is True, 'JSPI promise')
    return {'available': True, 'suspensions': 3, 'non_promising_error': jspi['non_promising_call']['error']}


def check_callback(cb):
    require(cb.get('available') is True and cb.get('memory') == 'unshared', 'CALLBACK available')
    require(value(cb.get('rmw_add'), 'CALLBACK rmw') == 0, 'CALLBACK rmw')
    require(value(cb.get('load_after_rmw'), 'CALLBACK load') == 5, 'CALLBACK load')
    require(value(cb.get('cmpxchg'), 'CALLBACK cmpxchg') == 5, 'CALLBACK cmpxchg')
    require(error_class(cb.get('wait'), 'CALLBACK wait') == 'RuntimeError', 'CALLBACK wait')
    require(value(cb.get('grow'), 'CALLBACK grow') == 1, 'CALLBACK grow')
    check_growth(cb.get('growth'), 0, 'CALLBACK')
    return {'available': True, 'unshared_wait': 'RuntimeError'}


def check(observed, engine, isolated=True):
    """Return the matrix row for one engine record or raise the first failure."""
    require(isinstance(observed, dict) and observed.get('page_failure') is None, 'PAGE failure')
    expected = FEATURES['engines'][engine]['expected_profiles']
    identity = observed.get('engine') or {}
    require(identity.get('kind') == FEATURES['engines'][engine]['kind'], 'ENGINE kind')
    api = observed.get('api') or {}
    if identity.get('kind') == 'browser':
        require(api.get('crossOriginIsolated') is isolated, 'ENGINE isolation')
    row = {'engine': engine, 'isolated_page': isolated if identity.get('kind') == 'browser' else None}
    row['detection'] = check_detection(observed)
    check_core(observed.get('core') or {})
    profiles = observed.get('profiles') or {}
    row['full'] = check_full(profiles.get('full') or {}, expected['full'] and isolated)
    row['single_thread_jspi'] = check_jspi(profiles.get('single_thread_jspi') or {}, expected['single_thread_jspi'])
    row['precompiled_callback'] = check_callback(profiles.get('precompiled_callback') or {})
    row['exception_encoding'] = 'final try_table/throw_ref executed; legacy validation ' + str(row['detection']['legacy-eh'])
    return row


LEGACY_MNEMONICS = {'try', 'catch', 'catch_all', 'delegate', 'rethrow'}
FINAL_MNEMONICS = {'try_table', 'throw', 'throw_ref'}


def encoding_pin(disassembly, require_final):
    """Classify the mnemonics of one disassembled binary under the encoding pin."""
    found = set()
    for line in disassembly.splitlines():
        if '|' not in line:
            continue
        text = line.split('|', 1)[1].strip()
        if not text:
            continue
        found.add(text.split()[0])
    legacy = sorted(found & LEGACY_MNEMONICS)
    final = sorted(found & FINAL_MNEMONICS)
    if legacy:
        raise ValueError('ENCODING legacy ' + ' '.join(legacy))
    if require_final and 'try_table' not in final:
        raise ValueError('ENCODING final missing')
    return {'legacy': legacy, 'final': final}
