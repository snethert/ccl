"""Each corruption must fail its own identity or phase-order obligation."""
from identity_join import check, key


def run(base, graph, witnesses, streams):
    result = []
    check(base, graph, witnesses, streams)
    def change(name, obj, field, value, reason):
        old = obj[field]; obj[field] = value
        try:
            try: check(base, graph, witnesses, streams)
            except ValueError as exc:
                if not str(exc).startswith(reason): raise AssertionError((name, str(exc), reason))
                result.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
            else: raise AssertionError(name + ' escaped')
        finally: obj[field] = old
    def edge(prefix): return next(e for e in graph['edges'] if e['evidence'].startswith(prefix))
    def init(prefix): return next(r for r in graph['initializers'] if r['node'].startswith(prefix))

    target = key('cold', 'code', streams['cold']['startup_calls'][0]['function'])
    change('callee-from-another-process', edge('build/callee/'), 'targets', [target], 'EXACT_EDGE')
    change('serialized-function-substitution', edge('build/loaded-code/'), 'targets', [target], 'EXACT_EDGE')
    change('materialization-substitution', edge('build/code-afunc/'), 'targets', [target], 'EXACT_EDGE')
    change('reader-function-substitution', edge('build/reader/'), 'targets', [target], 'EXACT_EDGE')
    change('callback-identity-substitution', edge('cold/callback-code/'), 'targets', [key('build', 'code', 1)], 'EXACT_EDGE')
    nested = next(e for e in streams['build']['effects'] if e['parent'] is not None)
    row = next(r for r in graph['initializers'] if r['node'] == key('build', 'boundary', nested['enter']))
    change('nested-effect-depends-on-own-return', row, 'prerequisites', [key('build', 'boundary', nested['return'])], 'EFFECT_ORDER')
    value = next(r for r in graph['initializers'] if r['node'].startswith('identity:build:') and 'values SHA256' in r['completion_assertion'])
    change('initializer-values-substitution', value, 'completion_assertion', 'Observed normal return with other values.', 'RESULT_WITNESS')
    image = next(r for r in graph['initializers'] if r['node'].startswith('identity:build:') and 'Queued Lisp execution NOT_OBSERVED.' in r['completion_assertion'])
    change('image-construction-claims-lisp-execution', image, 'completion_assertion', image['completion_assertion'].replace('Queued Lisp execution NOT_OBSERVED.', 'Queued Lisp execution completed.'), 'IMAGE_EXECUTION_PROMOTION')
    boot = next(n for n in graph['nodes'] if n['id'] == key('build', 'gap', 'boot-process'))
    change('boot-witness-concealed', boot, 'disposition', 'implemented', 'BOOT_SCOPE')
    gap = next(n for n in graph['nodes'] if n['id'] == key('build', 'gap', 'dependency-closure'))
    change('observed-call-treated-as-static-bound', gap, 'disposition', 'implemented', 'DEPENDENCY_SCOPE')
    change('loader-seed-removed', graph, 'seeds', graph['seeds'][1:], 'SEED_PRESERVATION')
    change('trace-relabelled-as-observed-build', graph, 'observed_modules', [key('build', 'module', '@execution')], 'TRACE_PRESERVATION')
    n = next(n for n in graph['nodes'] if n['id'].startswith('identity:build:boundary:'))
    change('effect-boundary-omitted', graph, 'nodes', [r for r in graph['nodes'] if r is not n], 'BOUNDARY_COVERAGE')
    check(base, graph, witnesses, streams)
    return {'status': 'PASS', 'controls': result, 'scope': 'Integration controls with distinct rejection reasons; the complete LL15 census is still blocked.'}
