"""Mutate actual projection joins. Require a new, specific coverage rejection."""
import copy
from check_exchange import check, Rejected
from exchange import ident
from opcodes import read_alist


def run(graph, joins, args):
    results = []
    def changed(name, object_, key, value, code):
        old = object_[key]
        object_[key] = value
        try:
            expect(name, code)
        finally:
            object_[key] = old
    def expect(name, code):
        try:
            check(graph, joins, *args)
        except Rejected as exc:
            if exc.code != code:
                raise AssertionError(f'{name}: expected {code}, got {exc}') from exc
            results.append({'control': name, 'status': 'REJECTED', 'code': exc.code, 'reason': str(exc)})
        else:
            raise AssertionError(name + ': incomplete projection accepted')
    def drop(name, rows, predicate, code):
        index = next(i for i, r in enumerate(rows) if predicate(r))
        row = rows.pop(index)
        try:
            expect(name, code)
        finally:
            rows.insert(index, row)
    def edge(prefix):
        return next(e for e in graph['edges'] if e['evidence'].startswith(prefix))
    check(graph, joins, *args)
    drop('required-function-node', graph['nodes'], lambda n: n['id'].startswith('compiled:'), 'NODE_COVERAGE')
    drop('required-call-edge', graph['edges'], lambda e: e['evidence'].startswith('r7/calls/') and e['resolution'] == 'complete', 'EDGE_COVERAGE')
    unknown = next(e for e in graph['edges'] if e['evidence'].startswith('r7/calls/') and e['resolution'] == 'unresolved')
    drop('concealed-unknown-call', graph['edges'], lambda e: e is unknown, 'UNKNOWN_CALL')
    changed('unjustified-call-bound', unknown, 'resolution', 'complete', 'UNKNOWN_CALL')
    changed('omitted-resident-candidates', unknown, 'targets',
            [t for t in unknown['targets'] if t != ident('module', '@clean-image')], 'CANDIDATE_OMISSION')
    image = args[0]
    load = ident('native', next(b['function'] for b in image['bindings'] if b['name'] == 'COMMON-LISP::LOAD' and b['namespace'] == 'function'))
    changed('loader-seed', graph, 'seeds', [s for s in graph['seeds'] if s != load], 'SEED_COVERAGE')
    old_args = args
    candidate_mutant = copy.deepcopy(args[2])
    candidate_mutant['seeds'] = [s for s in candidate_mutant['seeds'] if s['name'] != 'COMMON-LISP::LOAD']
    args = (*args[:2], candidate_mutant, *args[3:])
    try:
        changed('loader-seed-removed-from-proposal-too', graph, 'seeds', [s for s in graph['seeds'] if s != load], 'LOADER_SEED')
    finally:
        args = old_args
    changed('seed-review-promotion', graph, 'seed_review', 'ACCEPTED', 'REVIEW_PROMOTION')
    startup = next(i for i in graph['initializers'] if i['node'].startswith('init-startup:'))
    changed('initializer-cycle', startup, 'prerequisites', [startup['node']], 'STARTUP_PREREQUISITE')
    drop('emitted-initializer-omission', graph['initializers'], lambda r: r['node'].startswith('init-load:'), 'INITIALIZER_COVERAGE')
    emitted = next(i for i in graph['initializers'] if i['node'].startswith('init-load:'))
    changed('emission-relabeled-as-completion', emitted, 'completion_assertion', 'Executed successfully', 'INITIALIZER_PROMOTION')
    effect = next(e for e in joins['effects']['compile'] if e['compiled_during'])
    changed('initializer-body-hidden-from-witness', effect, 'compiled_during', [], 'EFFECT_BODY_OMISSION')
    other = next(e for e in joins['effects']['compile'] if e['return'] != effect['return'])
    changed('initializer-return-substitution', effect, 'return', other['return'], 'EFFECT_RETURN')
    changed('callback-code-substitution', edge('startup/code/'), 'targets', [load], 'EDGE_TARGETS')
    changed('handler-code-substitution', edge('image/handler-code/'), 'targets', [load], 'EDGE_TARGETS')
    changed('lowering-bound-promotion', edge('lowering/whole-native-template-candidates/'), 'resolution', 'complete', 'UNPROVED_PROMOTION')
    opcode = edge('lowering/opcode/')
    changed('template-opcode-substitution', opcode, 'targets', [load], 'EDGE_TARGETS')
    binding = next(e for e in graph['edges'] if e['evidence'].startswith('candidates/targets/') and len(e['targets']) > 1)
    changed('source-version-candidate-omission', binding, 'targets', binding['targets'][1:], 'BINDING_COVERAGE')
    drop('stub-call-omission', graph['edges'], lambda e: e['evidence'].startswith('stub/calls/') and e['resolution'] == 'complete', 'EDGE_COVERAGE')
    gap = next(n for n in graph['nodes'] if n['id'] == ident('gap', 'target-source-coverage'))
    changed('fourteen-forms-relabeled-full-source-coverage', gap, 'disposition', 'implemented', 'GAP_CONCEALED')
    changed('r5-trace-relabeled-r7-image', graph, 'observed_modules', [ident('module', '@clean-image')], 'TRACE_MODULES')
    drop('function-to-module-join', graph['edges'], lambda e: e['evidence'].startswith('provenance/'), 'EDGE_COVERAGE')
    changed('required-node-made-optional', graph['nodes'][0], 'required', False, 'REQUIRED_FLAG')
    check(graph, joins, *args)
    assert read_alist('((893 "SHRQ" 16 8) (516 "MOVQ" 8 8))') == [[893, 'SHRQ', 16, 8], [516, 'MOVQ', 8, 8]]
    assert read_alist('((1 "A" . #1=(8 8)) (2 "B" . #1#))') == [[1, 'A', 8, 8], [2, 'B', 8, 8]]
    syntax = []
    for name, text in [('read-eval', '#.(print 1)'), ('unreadable', '#<OBJECT>'), ('truncated', '((1 "A") ... )'),
                       ('unknown-label', '((1 "A" . #1#))'), ('duplicate-opcode', '((1 "A") (1 "B"))')]:
        try:
            read_alist(text)
        except ValueError:
            syntax.append({'control': name, 'status': 'REJECTED'})
        else:
            raise AssertionError(name + ': unsafe/malformed alist accepted')
    return {'status': 'PASS', 'scope': 'Retained-input projection controls. Original census is BLOCKED; '
            'each mutation must cause its own additional coverage failure. This is not LL15-c acceptance.',
            'positive': 'Complete retained-input coverage before and after mutations',
            'controls': results, 'opcode_parser_positive_cases': 2, 'opcode_parser_controls': syntax}
