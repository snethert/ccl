#!/usr/bin/env python3
"""Join native identities to r7 and prepare candidates for review, without claiming closure."""
import collections


def unique(rows, key, label):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('duplicate ' + label)
    return result


def build(image, observed, seeds):
    if image['version'] != 1 or observed['version'] != 1 or seeds['version'] != 1:
        raise ValueError('unsupported input version')
    native = unique(image['functions'], 'id', 'native code identity')
    compiled = unique(observed['nodes'], 'id', 'compiler object identity')
    if not native or not compiled:
        raise ValueError('empty code inventory')
    for f in native.values():
        if type(f['id']) is not int or f['id'] < 1 or set(f['literal_functions']) - native.keys():
            raise ValueError('invalid native code/literal identity')
    bindings = collections.defaultdict(list)
    for b in image['bindings']:
        if b['function'] not in native or b['namespace'] not in ('function', 'macro'):
            raise ValueError('invalid native binding')
        bindings[(b['namespace'], b['name'])].append(b)
    operators = unique(image['operators'], 'id', 'operator slot')
    if set(operators) != {o['id'] for o in observed['operators']}:
        raise ValueError('evaluated operator slots differ')
    for old in observed['operators']:
        new = operators[old['id']]
        if any(old[k] != new[k] for k in ('id', 'name', 'flags', 'encoded', 'handler')):
            raise ValueError('evaluated operator metadata differs')
        if new['function'] is not None and new['function'] not in native:
            raise ValueError('handler code identity absent')
        if (new['handler'] not in (None, 'NIL')) != (new['function'] is not None):
            raise ValueError('handler name/code identity mismatch')
    old_groups = observed['startup_groups']
    if [g['group'] for g in old_groups] != [g['group'] for g in image['startup_groups']]:
        raise ValueError('startup group inventory differs')
    for old, new in zip(old_groups, image['startup_groups']):
        if old['functions'] != [f['name'] for f in new['functions']]:
            raise ValueError('startup callback inventory/order differs')
        if any(f['function'] not in native for f in new['functions']):
            raise ValueError('callback code identity absent')
    joined_seeds = []
    for seed in seeds['entrypoints']:
        targets = bindings.get(('function', seed['name']), [])
        if len(targets) != 1:
            raise ValueError('seed lacks one native function binding: ' + seed['name'])
        joined_seeds.append({**seed, 'native_function': targets[0]['function']})
    if len({s['name'] for s in joined_seeds}) != len(joined_seeds):
        raise ValueError('duplicate seed')
    universe = {'id': 'native-image-and-r7-bodies',
                'native_functions': sorted(native), 'compiler_functions': sorted(compiled),
                'qualification': 'CANDIDATES_ONLY_NOT_A_PROVED_CLOSED_WORLD',
                'reason': 'Retain every resident code prototype and every observed compiler body; no address-taken pruning and no removal of older source versions. Static completeness, runtime installation effects and future generated code are not established by these two captures.'}
    dynamic = []
    for c in observed['calls']:
        if not c['dependency']['targets']:
            dynamic.append({'caller': c['caller'], 'site': c['site'],
                            'category': c['dependency']['category'],
                            'first_sequence': c['first_sequence'],
                            'candidates': universe['id'], 'resolution': 'UNQUALIFIED'})
    if {(c['caller'], c['site']) for c in dynamic} != {(c['caller'], c['site']) for c in observed['unresolved_calls']}:
        raise ValueError('dynamic-call worklist differs from observed calls')
    globals_ = []
    for b in observed['global_binding_candidates']:
        # A printed name proposes matches, never proves the active definition
        # at a past call. Preserve setter package identity and all collisions.
        globals_.append({'name': b['name'], 'compiler_functions': b['function_ids'],
                         'native_bindings': bindings.get(('function', b['name']), []),
                         'resolution': 'SNAPSHOT_AND_SOURCE_CANDIDATES_NOT_INSTALLATION_HISTORY'})
    result = {'version': 1, 'status': 'PREPARED_FOR_REVIEW', 'census_acceptance': 'BLOCKED',
              'scope': seeds['profile'], 'seed_review_disposition': seeds['review_disposition'],
              'seeds': joined_seeds, 'required_effects': seeds['required_effects'],
              'candidate_universe': universe, 'dynamic_calls': dynamic,
              'global_bindings': globals_, 'startup_groups': image['startup_groups'],
              'operator_handlers': image['operators'], 'scope_limits': seeds['scope_limits']}
    missing_before = [r for r in globals_ if not r['compiler_functions']]
    summary = {'status': result['status'], 'census_acceptance': 'BLOCKED',
               'native_functions_including_inspector': len(native), 'r7_compiler_bodies': len(compiled),
               'native_function_bindings': sum(b['namespace'] == 'function' for b in image['bindings']),
               'native_macro_bindings': sum(b['namespace'] == 'macro' for b in image['bindings']),
               'proposed_entrypoint_seeds': len(joined_seeds),
               'startup_callback_identities': sum(len(g['functions']) for g in image['startup_groups']),
               'operator_slots': len(operators),
               'operator_slots_with_handler_identity': sum(o['function'] is not None for o in image['operators']),
               'vinsn_templates': len(image['vinsns']), 'subprimitives': len(image['subprimitives']),
               'dynamic_calls_with_unqualified_candidates': len(dynamic),
               'global_bindings_without_compiler_candidate_before': len(missing_before),
               'of_those_with_native_binding_now': sum(bool(r['native_bindings']) for r in missing_before),
               'still_without_named_candidate': sum(not r['native_bindings'] for r in missing_before),
               'remaining': ['Independent seed and candidate-bound review',
                             'S0-LL08-a static reachability; prove or widen the finite universe',
                             'Operator-to-lowering/import/trap/store joins',
                             'Semantic compile/load/startup initializer prerequisite joins',
                             'Complete census exchange graph and independent omission witnesses']}
    return result, summary


def check_coverage(result, image, observed, seeds):
    """Check retained input witnesses, independently of the producer's summary counts."""
    universe = result['candidate_universe']
    for key, rows in [('native_functions', image['functions']), ('compiler_functions', observed['nodes'])]:
        values = universe[key]
        if len(values) != len(set(values)) or set(values) != {r['id'] for r in rows}:
            raise ValueError('candidate universe omitted/duplicated an input identity: ' + key)
    expected_calls = {(c['caller'], c['site'], c['first_sequence']) for c in observed['calls']
                      if not c['dependency']['targets']}
    actual_calls = {(c['caller'], c['site'], c['first_sequence']) for c in result['dynamic_calls']}
    if expected_calls != actual_calls or len(actual_calls) != len(result['dynamic_calls']):
        raise ValueError('dynamic call omitted or duplicated')
    if any(c['candidates'] != universe['id'] or c['resolution'] != 'UNQUALIFIED'
           for c in result['dynamic_calls']):
        raise ValueError('unproved call bound promoted or disconnected')
    if result['seed_review_disposition'] != seeds['review_disposition'] or result['census_acceptance'] != 'BLOCKED':
        raise ValueError('unreviewed preparation promoted to acceptance')
    required = {s['name'] for s in seeds['entrypoints']}
    # These are source-level entrypoint witnesses, not output summary counts.
    if not {'COMMON-LISP::READ', 'COMMON-LISP::LOAD', 'CCL::%FASLOAD',
            'CCL::RESTORE-LISP-POINTERS', 'COMMON-LISP::ERROR'}.issubset(required):
        raise ValueError('required reader/loader/startup/error seed removed')
    if {s['name'] for s in result['seeds']} != required or len(result['seeds']) != len(required):
        raise ValueError('proposed seed omitted or duplicated')
    for seed in result['seeds']:
        if not any(b['namespace'] == 'function' and b['name'] == seed['name'] and
                   b['function'] == seed['native_function'] for b in image['bindings']):
            raise ValueError('seed does not identify its native function binding')
    if result['startup_groups'] != image['startup_groups']:
        raise ValueError('startup callback identity changed')
    if result['operator_handlers'] != image['operators']:
        raise ValueError('evaluated handler identity changed')
    old_bindings = unique(observed['global_binding_candidates'], 'name', 'global name')
    new_bindings = unique(result['global_bindings'], 'name', 'joined global name')
    if set(old_bindings) != set(new_bindings):
        raise ValueError('global binding omitted')
    actual = collections.defaultdict(list)
    for b in image['bindings']:
        if b['namespace'] == 'function': actual[b['name']].append(b)
    for name, old in old_bindings.items():
        new = new_bindings[name]
        if new['compiler_functions'] != old['function_ids'] or new['native_bindings'] != actual[name]:
            raise ValueError('source version, setter identity or native binding omitted')
