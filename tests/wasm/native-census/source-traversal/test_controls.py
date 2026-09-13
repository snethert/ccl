"""Omissions and false qualification applied to the genuine source capture."""
from copy import deepcopy
from check import check_capture, check_projection


def run(capture, facts, source):
    rows = []
    def reject(name, object_, mutation, checker):
        altered = deepcopy(object_); mutation(altered)
        try:
            checker(altered)
        except ValueError as e:
            rows.append({'control': name, 'status': 'REJECTED', 'reason': str(e)})
        else:
            raise ValueError('CONTROL_ESCAPED: ' + name)
    check_c = lambda c: check_capture(c, source)
    def coordinated_boundary(c):
        for field in ('index', 'rows'):
            c[field][4]['end'] += 1
            c[field][5]['start'] += 1
    reject('shift-both-boundary-copies', capture, coordinated_boundary, check_c)
    for name, change in [
        ('omit-last-form', lambda c: c['rows'].pop()),
        ('end-after-first-capture', lambda c: c.update(rows=c['rows'][:1])),
        ('change-source-range', lambda c: c['rows'][4].update(start=0)),
        ('conceal-unread-tail', lambda c: c.update(eof=c['tail_start'])),
        ('host-reader-context', lambda c: c['rows'][8]['reader_context'].update(target_package='X8664')),
        ('hide-unsupported-definition', lambda c: c['rows'][5].update(status='TOPLEVEL-PROCESSED')),
        ('hide-prior-failure', lambda c: c['rows'][6].update(prior_unresolved_forms=[])),
        ('omit-macro-witness', lambda c: c['rows'][4].update(macro_expansions=[])),
        ('change-source-binding', lambda c: c.update(source_bindings_unchanged=False)),
        ('omit-source-call', lambda c: c['rows'][4]['function'].update(calls=[])),
    ]:
        reject(name, capture, change, check_c)
    check_f = lambda f: check_projection(f, capture)
    for name, change in [
        ('omit-function', lambda f: f['definitions'].pop()),
        ('insert-function', lambda f: f['definitions'].append(dict(f['definitions'][0], id=-1))),
        ('omit-call', lambda f: f['calls'].pop()),
        ('invent-call-target', lambda f: f['calls'][0]['record']['dependency'].update(targets=[])),
        ('omit-reference', lambda f: f['function_references'].pop()),
        ('omit-unsupported-form', lambda f: f['unsupported_forms'].pop()),
        ('promote-cached-macros', lambda f: f.update(macro_environment='QUALIFIED')),
        ('claim-closure', lambda f: f.update(census_acceptance='ACCEPTED')),
        ('claim-widening-replaced', lambda f: f.update(graph_replacement='COMPLETE')),
        ('insert-membership-edge', lambda f: f.update(edges=[{'module': f['source'], 'targets': 'all'}])),
    ]:
        reject(name, facts, change, check_f)
    return {'status': 'PASS', 'controls_rejected': len(rows), 'controls': rows,
            'scope': 'First-module collection and fact projection; not the LL15-c complete closure suite.'}
