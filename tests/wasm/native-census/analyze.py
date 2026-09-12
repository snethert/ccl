#!/usr/bin/env python3
"""Validate observed records and summarize coverage without inventing closure."""
import argparse
import collections
import json
from pathlib import Path


def read_events(path):
    events = []
    with path.open() as stream:
        for number, line in enumerate(stream, 1):
            event = json.loads(line)
            if event['sequence'] != number: raise ValueError('missing/duplicate event: ' + str(path))
            if event['kind'] == 'complete' and event['payload']['events_before_complete'] != number - 1:
                raise ValueError('incorrect event count: ' + str(path))
            events.append(event)
    if not events or events[-1]['kind'] != 'complete' or sum(e['kind'] == 'complete' for e in events) != 1:
        raise ValueError('missing/duplicate completion: ' + str(path))
    return events


def snapshot(events):
    rows = [e['payload'] for e in events if e['kind'] == 'snapshot']
    if len(rows) != 1: raise ValueError('expected exactly one evaluated snapshot')
    s = rows[0]; ops = s['operators']
    if not ops or [o['id'] for o in ops] != list(range(len(ops))):
        raise ValueError('operator slot missing or reordered')
    for o in ops:
        # U1 nxenv.lisp:92 reserves the low ten bits for operator identity.
        if type(o['flags']) is not int or o['flags'] < 0 or o['flags'] & 1023:
            raise ValueError('operator flags overlap the identity bits')
        if o['name'] is None:
            if o['encoded'] is not None or o['flags'] != 0: raise ValueError('reserved operator slot populated')
        elif o['encoded'] != o['flags'] | o['id']:
            raise ValueError('operator ID/flags disagree with evaluated lookup')
    if s['backend'] != 'KEYWORD::DARWINX8664' or s['host_backend'] != s['backend'] or s['word_bits'] != 64:
        raise ValueError('wrong native target state')
    return s


def functions(payload):
    yield payload
    for inner in payload['inner_functions']: yield from functions(inner)


def analyze(root):
    report = json.loads((root / 'results.json').read_text())
    if report['execution_status'] != 'PASS': raise ValueError('native run did not pass')
    baseline = snapshot(read_events(root / 'baseline-snapshot.jsonl'))
    observed = snapshot(read_events(root / 'observed-snapshot.jsonl'))
    if baseline != observed: raise ValueError('evaluated operators/backend/startup registrations changed')
    if not report['all_archived_sources_restored'] or not report.get('restored_fasls_identical'):
        raise ValueError('source or clean output restoration missing')
    build = read_events(root / 'observed-rebuild.jsonl')
    probe = read_events(root / 'observed-probe.jsonl')
    cold = read_events(root / 'observed-cold-start.jsonl')
    tests = read_events(root / 'observed-tests/events.jsonl')
    for stream in (build, probe):
        kinds = collections.Counter(e['kind'] for e in stream)
        for required in ['read', 'macroexpand', 'frontend', 'before-pass2', 'compile-initializer-enter',
                         'compile-initializer-return', 'load-initializer-emitted']:
            if not kinds[required]: raise ValueError('unobserved phase ' + required)
        if kinds['compile-initializer-enter'] != kinds['compile-initializer-return']:
            raise ValueError('compile initializer did not return')
    expected_probe = {'COMMON-LISP-USER::CENSUS-PROBE-LEAF', 'COMMON-LISP-USER::CENSUS-PROBE-PARENT',
                      'COMMON-LISP-USER::CENSUS-PROBE-INDIRECT', 'COMMON-LISP-USER::CENSUS-PROBE-VALUES'}
    probe_functions = [f for e in probe if e['kind'] == 'before-pass2' for f in functions(e['payload'])]
    if not expected_probe.issubset({f['name'] for f in probe_functions}):
        raise ValueError('missing independently named probe function')
    by_name = {f['name']: f for f in probe_functions}
    if not by_name['COMMON-LISP-USER::CENSUS-PROBE-PARENT']['calls']:
        raise ValueError('required direct-call observation absent')
    if not any(c['target'] is None for c in by_name['COMMON-LISP-USER::CENSUS-PROBE-INDIRECT']['calls']):
        raise ValueError('unknown indirect call was hidden')
    expected_startup = [name for g in baseline['startup_groups'] for name in g['functions']]
    enters = [e['payload'] for e in cold if e['kind'] == 'startup-enter']
    returns = [e['payload'] for e in cold if e['kind'] == 'startup-return']
    if enters != expected_startup or returns != expected_startup:
        raise ValueError('startup callback order/completion differs from evaluated registrations')
    flow = [e['kind'] for e in cold if e['kind'].startswith('startup-')]
    if flow != ['startup-enter', 'startup-return'] * len(expected_startup):
        raise ValueError('startup callbacks overlap or fail to return')
    counts = collections.Counter(); calls = []; compiled = 0; sources = set()
    for e in build:
        if e['source']: sources.add(e['source'])
        if e['kind'] == 'before-pass2':
            for f in functions(e['payload']):
                compiled += 1
                counts.update({row['id']: row['count'] for row in f['operators']})
                calls.extend(f['calls'])
    return {'status': 'PASS', 'scope': 'Native observation, reversible patch and R6/R6a comparison only',
            'operator_slots': len(baseline['operators']),
            'reserved_slots': sum(o['name'] is None for o in baseline['operators']),
            'native_vinsn_templates': len(baseline['vinsn_templates']),
            'compiled_function_observations': compiled, 'compilation_sources_observed': len(sources),
            'observed_operator_ids': sorted(counts), 'unobserved_operator_ids': sorted(set(range(len(baseline['operators']))) - set(counts)),
            'call_forms_observed': len(calls), 'unknown_call_forms_retained': sum(c['target'] is None for c in calls),
            'startup_callbacks_entered_and_returned': len(enters),
            'events': {'build': len(build), 'probe': len(probe), 'cold_start': len(cold), 'tests': len(tests)},
            'phase_counts': dict(collections.Counter(e['kind'] for e in build)),
            'source_files': sorted(sources), 'census_acceptance': 'BLOCKED',
            'remaining': ['privileged external macOS file-operation trace and load-order reconciliation',
                          'reviewed seed set and conservative closure of every required dependency',
                          'complete lowering/import/trap/store joins and initializer prerequisite semantics',
                          'independent review of this observation patch and its evidence'],
            'claims_not_made': ['Wasm backend or generated Wasm code', 'complete S0-LL15-b/c census',
                                'callback order proves semantic initializer prerequisites',
                                'observed call forms enumerate every possible callee']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('run', type=Path); args = p.parse_args()
    try: print(json.dumps(analyze(args.run), indent=2))
    except (ValueError, KeyError, OSError) as exc: p.exit(1, 'FAIL: ' + str(exc) + '\n')
