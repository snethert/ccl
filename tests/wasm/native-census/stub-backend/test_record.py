#!/usr/bin/env python3
"""Semantic producer controls over the actual run, without copying/rebuilding prerequisites."""
import argparse
import copy
import json
from pathlib import Path
from record import load_inputs, validate
from reversible import save


def run(root):
    original = load_inputs(root); validate(original); results = []
    def reject(name, mutate):
        data = copy.deepcopy(original); mutate(data)
        try: validate(data)
        except ValueError as exc: results.append({'control': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise ValueError('producer control escaped: ' + name)
    reject('native-test-failure', lambda d: d['results.json']['registered_tests'].update(failed=1))
    reject('missing-native-fasl', lambda d: d['baseline-fasls.json'].pop(next(iter(d['baseline-fasls.json']))))
    reject('unexplained-native-difference', lambda d: d['registered-fasls.json'].update({next(n for n in d['baseline-fasls.json'] if n != 'bin/systems.dx64fsl'): '0' * 64}))
    reject('failed-output-reversal', lambda d: d['restored-fasls.json'].update({'bin/systems.dx64fsl': '0' * 64}))
    reject('active-source-unit', lambda d: d['results.json']['registration_restoration'].update(active=True))
    reject('changed-native-operator', lambda d: d['registered-snapshot.json']['snapshot']['operators'][1].update(flags=-1))
    reject('changed-existing-registration', lambda d: d['registered-snapshot.json']['modules'][0].update(binary='wrong-module'))
    reject('missing-target-control', lambda d: d['target-results.json']['outcomes'].pop())
    def positives(d, mutate):
        for mode in ['clean-1', 'clean-2']: mutate(d['target-sessions/' + mode + '.json'])
    reject('host-width-in-both-sessions', lambda d: positives(d, lambda r: next(row for row in r['rows'] if row['name'] == 'WORD-WIDTH').update(literals=[['COMMON-LISP::FIXNUM', '64']])))
    reject('fabricated-dynamic-resolution', lambda d: positives(d, lambda r: next(row for row in r['rows'] if row['name'] == 'DYNAMIC-CALL')['function']['calls'][0]['dependency'].update(targets=[{'kind': 'function', 'id': 1}])) )
    reject('omitted-unit-control', lambda d: d['unit-controls.json']['controls'].pop())
    return {'status': 'PASS', 'positive': 'Retained native/target run qualifies', 'controls': results,
            'scope': 'Semantic mutations in memory; no repeated raw artifact/archive verification.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--run', required=True, type=Path)
    a = p.parse_args(); target = a.run / 'producer-controls.json'
    if target.exists(): p.error('never overwrite a retained result')
    r = run(a.run); save(target, r)
    print(json.dumps({'status': r['status'], 'controls_rejected': len(r['controls'])}))
