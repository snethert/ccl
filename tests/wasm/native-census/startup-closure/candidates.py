#!/usr/bin/env python3
"""Join native identities to r7 and prepare candidates for review, without claiming closure."""
import collections


def unique(rows, key, label):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('duplicate ' + label)
    return result


def kernel_inputs(image, seeds):
    """Validate the new entry witnesses without inferring historical bindings."""
    if seeds['version'] == 1:
        return None
    k = image.get('kernel_entries')
    if not k or k['application_class'] != 'CCL::LISP-DEVELOPMENT-SYSTEM':
        raise ValueError('kernel entry snapshot or application class missing')
    native = {f['id'] for f in image['functions']}
    for field in ('callbacks', 'builtins'):
        rows = k[field]
        if [r['slot'] for r in rows] != list(range(len(rows))):
            raise ValueError('kernel vector slot coverage: ' + field)
        for r in rows:
            if r['function'] is None:
                if field != 'callbacks' or r['name'] is not None or r['symbol_value_matches'] is not None:
                    raise ValueError('invalid empty callback slot')
            elif r['function'] not in native:
                raise ValueError('kernel vector target absent: ' + field)
    required = {r['name']: r for r in seeds['required_bindings']}
    if len(required) != 2 or set(required) != {'CCL::%PASCAL-FUNCTIONS%', 'CCL::%BUILTIN-FUNCTIONS%'}:
        raise ValueError('required kernel vector omitted or duplicated')
    if (len(k['builtins']) != 23 or [r['name'] for r in k['builtins']] !=
            required['CCL::%BUILTIN-FUNCTIONS%']['expected_names']):
        raise ValueError('builtin slot order or source inventory differs')
    for row in k['builtins']:
        if not any(b['namespace'] == 'function' and b['name'] == row['name'] and
                   b['function'] == row['function'] for b in image['bindings']):
            raise ValueError('builtin function-cell identity differs')
    callback_names = ['CCL::XCMAIN', 'CCL::%XERR-DISP']
    for name in callback_names:
        found = [r for r in k['callbacks'] if r['name'] == name]
        if len(found) != 1 or not found[0]['symbol_value_matches'] or found[0]['function'] is None:
            raise ValueError('kernel callback lacks a matching trampoline: ' + name)
    methods = k['toplevel_methods']
    signatures = [(tuple(r['qualifiers']), tuple(r['specializers'])) for r in methods]
    # U1 defines a before method and two primaries. All three are applicable;
    # the less-specific primary is retained without claiming it executes.
    expected = {(('KEYWORD::BEFORE',), ('CCL::APPLICATION', 'COMMON-LISP::T')),
                ((), ('CCL::APPLICATION', 'COMMON-LISP::T')),
                ((), ('CCL::LISP-DEVELOPMENT-SYSTEM', 'COMMON-LISP::T'))}
    if (len(methods) != 3 or set(signatures) != expected or
            any(r['function'] not in native or r['generic'] != 'CCL::TOPLEVEL-FUNCTION' for r in methods)):
        raise ValueError('applicable toplevel methods differ from U1 source')
    if (len(seeds['method_seeds']) != 1 or seeds['method_seeds'][0]['generic'] != 'CCL::TOPLEVEL-FUNCTION' or
        seeds['method_seeds'][0]['argument_classes'] != ['CCL::LISP-DEVELOPMENT-SYSTEM', 'COMMON-LISP::NULL'] or
        seeds['method_seeds'][0]['selection'] != 'all-applicable-methods'):
        raise ValueError('required toplevel method selection changed')
    names = {s['name']: s for s in seeds['entrypoints']}
    for name in ['RESTORE-LISP-POINTERS', '%REVIVE-SYSTEM-LOCKS', 'REFRESH-EXTERNAL-ENTRYPOINTS',
                 'RESTORE-PASCAL-FUNCTIONS', 'INITIALIZE-INTERACTIVE-STREAMS', 'STARTUP-CCL',
                 'TOPLEVEL-FUNCTION', '%FASLOAD', 'REBUILD-CCL', '%SET-TOPLEVEL',
                 'MAKE-MCL-LISTENER-PROCESS', 'HOUSEKEEPING-LOOP', 'TOPLEVEL', 'LISTENER-FUNCTION',
                 'THREAD-MAKE-STARTUP-FUNCTION', '%PASCAL-FUNCTIONS%']:
        if names.get('CCL::' + name, {}).get('binding_kind') != 'function':
            raise ValueError('kernel source entry omitted: ' + name)
    for name in ['READ', 'LOAD', 'COMPILE-FILE', 'ERROR']:
        if names.get('COMMON-LISP::' + name, {}).get('binding_kind') != 'function':
            raise ValueError('workload source entry omitted: ' + name)
    if any(names.get(name, {}).get('binding_kind') != 'callback' for name in callback_names):
        raise ValueError('kernel callback seed omitted or treated as function cell')
    if not any(r['name'] == 'CCL::%FOREIGN-THREAD-CONTROL' and r['reason'] and r['scope']
               for r in seeds['exclusions']):
        raise ValueError('foreign-thread root exclusion not stated')
    return k


def build(image, observed, seeds):
    if image['version'] != 1 or observed['version'] != 1 or seeds['version'] not in (1, 2):
        raise ValueError('unsupported input version')
    kernel = kernel_inputs(image, seeds)
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
        kind = seed.get('binding_kind', 'function')
        if kind not in ('function', 'callback'):
            raise ValueError('unsupported seed binding kind')
        targets = ([r for r in kernel['callbacks'] if r['name'] == seed['name']]
                   if kind == 'callback' else bindings.get(('function', seed['name']), []))
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
    if kernel:
        result.update(version=2, seed_revision=seeds['revision'], kernel_entries=kernel,
                      method_seeds=kernel['toplevel_methods'], required_bindings=seeds['required_bindings'],
                      exclusions=seeds['exclusions'],
                      root_functions=sorted({s['native_function'] for s in joined_seeds} |
                          {r['function'] for r in kernel['toplevel_methods']} |
                          {r['function'] for r in kernel['callbacks'] + kernel['builtins'] if r['function'] is not None}),
                      root_scope='Snapshot roots only. No save/restore equality, future registration bound or static closure claimed.')
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
    if kernel:
        summary.update(seed_revision=seeds['revision'], root_functions=len(result['root_functions']),
                       applicable_toplevel_methods=len(kernel['toplevel_methods']), builtin_slots=len(kernel['builtins']),
                       callback_slots=len(kernel['callbacks']), live_callback_slots=sum(r['function'] is not None for r in kernel['callbacks']),
                       kernel_vector_scope=kernel['descriptor_time'])
    return result, summary


def check_coverage(result, image, observed, seeds):
    """Check retained input witnesses, independently of the producer's summary counts."""
    kernel = kernel_inputs(image, seeds)
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
        proposal = next(s for s in seeds['entrypoints'] if s['name'] == seed['name'])
        rows = (kernel['callbacks'] if proposal.get('binding_kind') == 'callback' else
                [b for b in image['bindings'] if b['namespace'] == 'function'])
        if any(seed.get(k) != v for k, v in proposal.items()) or not any(
                b['name'] == seed['name'] and b['function'] == seed['native_function'] for b in rows):
            raise ValueError('seed does not identify its native function binding')
    if kernel:
        if result['version'] != 2 or result['seed_revision'] != seeds['revision']:
            raise ValueError('seed revision changed')
        for field, expected in [('kernel_entries', kernel), ('method_seeds', kernel['toplevel_methods']),
                                ('required_bindings', seeds['required_bindings']), ('exclusions', seeds['exclusions'])]:
            if result[field] != expected:
                raise ValueError('kernel witness changed: ' + field)
        expected = {s['native_function'] for s in result['seeds']}
        expected.update(r['function'] for r in kernel['toplevel_methods'])
        expected.update(r['function'] for r in kernel['callbacks'] + kernel['builtins'] if r['function'] is not None)
        if result['root_functions'] != sorted(expected):
            raise ValueError('kernel root target omitted or duplicated')
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
