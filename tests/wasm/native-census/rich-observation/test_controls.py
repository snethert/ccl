#!/usr/bin/env python3
"""Exercise semantic omissions independently of event-count and schema checks."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
from check import check_probe


def test(data):
    positive = check_probe(data); outcomes = []
    def reject(name, mutation):
        damaged = deepcopy(data); mutation(damaged)
        try: check_probe(damaged)
        except ValueError as exc: outcomes.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise ValueError('semantic control escaped: ' + name)
    reject('drop-function-installation', lambda d: d['bindings'].remove(next(r for r in d['bindings'] if r['symbol']['name'] == 'RICH-VERSION')))
    reject('drop-macro-installation', lambda d: d['bindings'].remove(next(r for r in d['bindings'] if r['symbol']['name'] == 'RICH-MACRO')))
    reject('collapse-old-function-version', lambda d: next(r for r in d['bindings'] if r['symbol']['name'] == 'RICH-VERSION').update(function=[r['function'] for r in d['bindings'] if r['symbol']['name'] == 'RICH-VERSION'][1]))
    reject('erase-setf-cell-origin', lambda d: next(r for r in d['bindings'] if r['symbol']['setter_of'])['symbol'].update(setter_of=None))
    reject('erase-fasl-write-join', lambda d: d['fasl_reads'][0].update(written=None))
    reject('mislabel-native-reader', lambda d: d['fasl_reads'][0].update(reader_mode='cross-dump'))
    reject('wrong-materialization-identity', lambda d: d['fasl_reads'][0]['written'].update(function=-1))
    reject('unobserved-loader-function-installed', lambda d: next(r for r in d['bindings'] if r['source'] is None).update(function=-1))
    reject('erase-real-expansion-identities', lambda d: d.update(expanders=[]))
    reject('conceal-computed-call', lambda d: next(r for r in d['functions'] if r['name'] == 'COMMON-LISP-USER::RICH-INDIRECT').update(calls=[]))
    reject('erase-compile-call-join', lambda d: d['compile_calls'][0].update(function=-1))
    reject('erase-load-call-join', lambda d: d['load_calls'][0].update(code_origin={'origin': 'not-joined'}))
    reject('erase-loader-completions', lambda d: d.update(effects=[r for r in d['effects'] if r['family'] != 'fasl-effect']))
    reject('erase-native-handler-context', lambda d: d['emissions'][0].update(frames=[]))
    reject('omit-initializer-phase', lambda d: d['effect_schedule'].pop())
    reject('cyclic-initializer-phase', lambda d: d['effect_schedule'][0].update(prerequisite_boundary=d['effect_schedule'][0]['event']))
    return {'positive': positive, 'controls_rejected': len(outcomes), 'outcomes': outcomes}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('joins', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args()
    with gzip.open(a.joins, 'rt') as stream: result = test(json.load(stream))
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'positive': result['positive'], 'controls_rejected': result['controls_rejected']}))
