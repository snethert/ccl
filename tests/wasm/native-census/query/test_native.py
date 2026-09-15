"""Literal behavior oracles for the call-site probe, including U1 GETF-TEST."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from native import execute, save

HERE = Path(__file__).resolve().parent
CASES = [
    ('one-value', 'PROBE-FORWARD', '(lambda (fn) (funcall fn (function 1+) 4))', '(:RETURNED (5))', 1),
    ('all-values', 'PROBE-FORWARD', '(lambda (fn) (multiple-value-list (funcall fn (lambda (x) (values x (+ x 1) (+ x 2))) 4)))', '(:RETURNED ((4 5 6)))', 1),
    ('zero-values', 'PROBE-FORWARD', '(lambda (fn) (length (multiple-value-list (funcall fn (lambda (x) (declare (ignore x)) (values)) 4))))', '(:RETURNED (0))', 1),
    ('spread', 'PROBE-SPREAD', '(lambda (fn) (funcall fn (function +) (list 1 2 3 4 5)))', '(:RETURNED (15))', 1),
    ('evaluation-order', 'PROBE-ORDER', '''(lambda (fn) (let ((order nil))
      (let ((answer (funcall fn
        (lambda () (push 1 order) (lambda (a b) (push 4 order) (+ a b)))
        (lambda () (push 2 order) 10) (lambda () (push 3 order) 20))))
        (values answer (reverse order)))))''', '(:RETURNED (30 (1 2 3 4)))', 1),
    ('late-symbol-value', 'PROBE-SYMBOL', '''(lambda (fn) (let ((name (gensym)))
      (unwind-protect (progn (setf (symbol-function name) (lambda (x) (declare (ignore x)) 10))
        (funcall fn name (lambda () (setf (symbol-function name) (lambda (x) (declare (ignore x)) 20)) 7)))
        (fmakunbound name))))''', '(:RETURNED (20))', 1),
    ('escaping-closure', 'PROBE-CLOSURE', '(lambda (fn) (let ((f (funcall fn (function 1+)))) (list (funcall f 3) (funcall f 8))))', '(:RETURNED ((4 9)))', 2),
    ('nonlocal-cleanup', 'PROBE-UNWIND', '''(lambda (fn) (let ((effect 0))
      (list (catch :out (funcall fn (lambda () (throw :out :escaped)) (lambda () (incf effect))) (error "must not run")) effect)))''', '(:RETURNED ((:ESCAPED 1)))', 1),
    ('callee-condition', 'PROBE-FORWARD', '(lambda (fn) (handler-case (funcall fn (lambda (x) (declare (ignore x)) (error "expected")) 2) (simple-error () :caught)))', '(:RETURNED (:CAUGHT))', 1),
    ('not-reached', 'PROBE-FORWARD', '(lambda (fn) (declare (ignore fn)) :not-called)', '(:RETURNED (:NOT-CALLED))', 0),
    ('budget', 'PROBE-FORWARD', '(lambda (fn) (loop for i below 10 sum (funcall fn (function 1+) i)))', '(:RETURNED (55))', 10),
]


def run(a):
    a.output.mkdir(parents=True, exist_ok=False)
    selections = {}; results = []
    for case, name, scenario, expected, count in CASES:
        function = 'CCL-CENSUS-QUERY::' + name
        if name not in selections:
            listing = execute(a.source, HERE / 'probe-input.lisp', function, a.image, a.kernel, a.output / ('sites-' + name))
            selections[name] = listing['selections'][0]
        inp = a.output / (case + '.lisp'); inp.write_text(scenario + '\n')
        answer = execute(a.source, HERE / 'probe-input.lisp', function, a.image, a.kernel, a.output / case,
                         scenario=inp, selection=selections[name], limit=2 if case == 'budget' else 10000)
        native = answer['native']
        assert native['scenario_result'] == expected, (case, native['scenario_result'], expected)
        assert native['total_events'] == count and len(native['events']) == min(count, 2 if case == 'budget' else 10000)
        assert answer['status'] == ('TRUNCATED' if case == 'budget' else 'NOT_REACHED' if not count else 'PASS')
        assert not answer['exhaustive'] and native['scenario_equal'] and native['restored_code_identical']
        results.append(dict(case=case, status='PASS', events=count))
    # A real U1 definition, selected from its source rather than a synthetic lambda.
    function = 'CCL::GETF-TEST'; source = a.source / 'level-1/l1-utils.lisp'
    listing = execute(a.source, source, function, a.image, a.kernel, a.output / 'u1-sites')
    inp = a.output / 'u1-scenario.lisp'
    inp.write_text('(lambda (fn) (funcall fn (list :a 10 :b 20) :b (function eq)))\n')
    answer = execute(a.source, source, function, a.image, a.kernel, a.output / 'u1-witness',
                     scenario=inp, selection=listing['selections'][0])
    assert answer['native']['scenario_result'] == '(:RETURNED (20))' and answer['native']['total_events'] == 2
    results.append(dict(case='U1-GETF-TEST', status='PASS', events=2))
    for name, change, reason in [
        ('wrong-source', lambda s: s.update(source_sha256='0' * 64), 'another source'),
        ('wrong-function', lambda s: s.update(function='CCL::OTHER'), 'another source'),
        ('wrong-site-path', lambda s: s['site'].update(acode_path=['wrong']), 'site identity'),
        ('absent-site', lambda s: s['site'].update(index=9999), 'native query failed')]:
        bad = deepcopy(listing['selections'][0]); change(bad)
        try: execute(a.source, source, function, a.image, a.kernel, a.output / name, scenario=inp, selection=bad)
        except ValueError as error: assert reason in str(error), (name, str(error))
        else: raise AssertionError('control escaped: ' + name)
        results.append(dict(case=name, status='REJECTED'))
    text = (HERE / 'site-probe.lisp').read_text()
    mutants = [
        ('discard-secondary-values', 'all-values', '(apply (or function designator) args)', '(values (apply (or function designator) args))'),
        ('omit-witness-events', 'one-value', '(when (<= *total* *limit*)', '(when nil'),
        ('omit-instrumentation', 'one-value', '(when instrument (rewrite-call node))', '(when nil (rewrite-call node))'),
        ('swallow-nonlocal-exit', 'nonlocal-cleanup', '(apply (or function designator) args)', '(catch :out (apply (or function designator) args))'),
    ]
    for name, case, old, new in mutants:
        assert text.count(old) == 1
        observer = a.output / (name + '.lisp'); observer.write_text(text.replace(old, new))
        spec = next(r for r in CASES if r[0] == case)
        function = 'CCL-CENSUS-QUERY::' + spec[1]
        try:
            answer = execute(a.source, HERE / 'probe-input.lisp', function, a.image, a.kernel, a.output / name,
                scenario=a.output / (case + '.lisp'), selection=selections[spec[1]], observer_path=observer)
        except ValueError as error:
            assert 'native query failed' in str(error) or 'event coverage' in str(error), str(error)
        else:
            assert answer['status'] != 'PASS' or answer['native']['scenario_result'] != spec[3] or answer['native']['total_events'] != spec[4], name
        results.append(dict(case=name, status='REJECTED'))
    save(a.output / 'summary.json', dict(status='PASS', cases=results, source='native U1 plus explicitly synthetic controls', gate_credit=False))
    print('PASS', len(results), 'native probe cases')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'image', 'kernel', 'output'): p.add_argument('--' + name, type=Path, required=True)
    run(p.parse_args())
