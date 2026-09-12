#!/usr/bin/env python3
"""Omission and identity controls for the candidate preparation, not LL15 qualification."""
import copy
from candidates import build, check_coverage


def run(image, observed, seeds):
    result, _ = build(image, observed, seeds)
    check_coverage(result, image, observed, seeds)
    controls = []
    def reject(name, action):
        try: action()
        except ValueError as exc: controls.append({'control': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise ValueError('control escaped: ' + name)
    def mutate_output(action):
        changed = copy.deepcopy(result); action(changed)
        check_coverage(changed, image, observed, seeds)
    reject('omit-resident-code', lambda: mutate_output(lambda r: r['candidate_universe']['native_functions'].pop()))
    reject('omit-compiled-body', lambda: mutate_output(lambda r: r['candidate_universe']['compiler_functions'].pop()))
    reject('conceal-dynamic-call', lambda: mutate_output(lambda r: r['dynamic_calls'].pop()))
    reject('claim-unproved-bound', lambda: mutate_output(lambda r: r['dynamic_calls'][0].update(resolution='COMPLETE')))
    reject('remove-loader-seed', lambda: mutate_output(lambda r: r.update(seeds=[s for s in r['seeds'] if s['name'] != 'CCL::%FASLOAD'])))
    reject('change-callback-identity', lambda: mutate_output(lambda r: r['startup_groups'][0]['functions'][0].update(function=-1)))
    reject('change-handler-identity', lambda: mutate_output(lambda r: next(o for o in r['operator_handlers'] if o['function']).update(function=-1)))
    reject('discard-source-version', lambda: mutate_output(lambda r: next(b for b in r['global_bindings'] if b['compiler_functions'])['compiler_functions'].pop()))
    reject('discard-native-binding', lambda: mutate_output(lambda r: next(b for b in r['global_bindings'] if b['native_bindings'])['native_bindings'].pop()))
    reject('claim-acceptance', lambda: mutate_output(lambda r: r.update(census_acceptance='ACCEPTED')))
    broken = copy.deepcopy(image); broken['functions'][0]['literal_functions'].append(-1)
    reject('unknown-literal-code', lambda: build(broken, observed, seeds))
    broken = copy.deepcopy(image); broken['operators'].pop()
    reject('missing-operator-slot', lambda: build(broken, observed, seeds))
    broken = copy.deepcopy(image); broken['startup_groups'][0]['functions'].pop()
    reject('missing-startup-callback', lambda: build(broken, observed, seeds))
    # Same printed uninterned SETF name, distinct package identities and code.
    # This is an analysis control, not a native execution/rebinding claim.
    collision = copy.deepcopy(image)
    binding = next(b for b in collision['bindings'] if b['setter_of'] and
                   any(g['name'] == b['name'] for g in observed['global_binding_candidates']))
    other = dict(binding, setter_of='CENSUS-CONTROL::COLLIDING-SETTER',
                 function=next(f['id'] for f in image['functions'] if f['id'] != binding['function']))
    collision['bindings'].append(other)
    joined, _ = build(collision, observed, seeds)
    check_coverage(joined, collision, observed, seeds)
    row = next(b for b in joined['global_bindings'] if b['name'] == binding['name'])
    if binding not in row['native_bindings'] or other not in row['native_bindings']:
        raise ValueError('setter collision merged')
    row['native_bindings'].remove(other)
    reject('collapse-setter-package-collision', lambda: check_coverage(joined, collision, observed, seeds))
    return {'status': 'PASS', 'positive_cases': ['retained-inputs', 'distinct-setter-packages'],
            'controls': controls, 'scope': 'Candidate retention/identity controls; not the LL15 closure omission suite.'}
