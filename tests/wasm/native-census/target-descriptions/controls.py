"""Controls for the metadata, complete function capture and retained obligations."""
from copy import deepcopy
from analysis import check_capture, check_projection, check_descriptions, functions


def run(capture, facts, descriptions, source):
    rows = []
    def reject(name, original, mutate, checker):
        value = deepcopy(original); mutate(value)
        try: checker(value)
        except ValueError as e: rows.append(dict(control=name, status='REJECTED', reason=str(e)))
        else: raise ValueError('CONTROL_ESCAPED: '+name)
    def remove_restore_call(c):
        f = c['rows'][14]['function']
        f['calls'] = [s for s in f['calls'] if not any(t.get('name') == 'CCL::RESTORE-PASCAL-FUNCTIONS'
                                                      for t in s['dependency']['targets'])]
    def hide_indirect(c):
        s = next(s for f in functions(c['rows'][14]['function']) for s in f['calls'] if not s['dependency']['targets'])
        s['dependency']['targets'] = [dict(kind='global-binding', name='CCL::INVENTED-CALLBACK')]
    def alias(c): c['load_time_links'][0]['initializer_id'] = c['load_time_links'][1]['initializer_id']
    for name, change in [
        ('omit-source-form', lambda c: c['rows'].pop()),
        ('omit-subtype', lambda c: c['types'].pop()),
        ('change-target-constant', lambda c: c['constants'][1].update(value=115)),
        ('host-context', lambda c: c['rows'][14]['reader_context'].update(word_bits=64)),
        ('hide-earlier-gap', lambda c: c['rows'][14].update(prior_unresolved_forms=[])),
        ('initializer-instead-of-definition', lambda c: c['rows'][5].update(function=c['load_time_initializers'][0]['function'])),
        ('omit-startup-call', remove_restore_call), ('conceal-indirect-call', hide_indirect),
        ('omit-initializer', lambda c: c['load_time_initializers'].pop()),
        ('omit-initializer-link', lambda c: c['load_time_links'].pop()),
        ('alias-initializer-identities', alias),
        ('invent-initializer-owner', lambda c: c['load_time_initializers'][0].update(owner_id=-1)),
        ('claim-initializer-executed', lambda c: c['load_time_initializers'][0].update(executed=True)),
        ('replace-deferred-token', lambda c: c['load_time_initializers'][0].update(deferred_token_matches=False)),
        ('lose-nonlocal-restoration', lambda c: c.update(nonlocal_description_state_restored=False)),
    ]:
        reject(name, capture, change, lambda c: check_capture(c, source, descriptions))
    for name, change in [
        ('omit-boundary-contract', lambda f: f['boundary_obligations'].pop()),
        ('accept-unimplemented-service', lambda f: f['boundary_obligations'][0].update(disposition='implemented')),
        ('omit-load-time-call', lambda f: f['load_time_initializers'][0]['function'].update(calls=[])),
        ('invent-load-time-edge', lambda f: f['load_time_links'].append(dict(f['load_time_links'][0]))),
        ('omit-runtime-call', lambda f: f['source_facts']['calls'].pop()),
        ('claim-qualified-macros', lambda f: f.update(macro_environment_qualified=True)),
        ('claim-complete-closure', lambda f: f.update(census_acceptance='ACCEPTED')),
    ]:
        reject(name, facts, change, lambda f: check_projection(f, capture, descriptions))
    for name, change in [
        ('wrong-source-derived-tag', lambda d: d['layout'][0].update(subtag=51)),
        ('borrow-native-kernel-offset', lambda d: d['contracts'][0].update(implementation='native offset')),
        ('declare-required-startup-unsupported', lambda d: d['contracts'][0].update(disposition='unsupported')),
        ('omit-required-boundary', lambda d: d['contracts'].pop()),
    ]:
        reject(name, descriptions, change, check_descriptions)
    return dict(status='PASS', controls_rejected=len(rows), controls=rows)
