"""Regression controls for source-origin privileges, including the reviewed bug."""
import subprocess
from pathlib import Path
import conditions
from support import HERE, require, read, save


def compile_probe(evidence, out, backend, sources, cases, refusals):
    old = conditions.SOURCES, conditions.cases, conditions.REFUSALS
    try:
        conditions.SOURCES = sources
        conditions.cases = lambda: cases
        conditions.REFUSALS = refusals
        conditions.compile_conditions(evidence, out, backend)
    finally:
        conditions.SOURCES, conditions.cases, conditions.REFUSALS = old


def run(evidence, out):
    require(not out.exists(), 'NO_OVERWRITE')
    out.mkdir()
    source = (HERE / 'wasm32-backend.lisp').read_text()
    guard = '(unless expanding (refuse :b-condition-generated-form))'
    require(source.count(guard) == 3, 'GENERATED_FORM_GUARDS')
    mutations = {
        'unscoped-case': (source.replace(guard, '', 3), 'user-case-nil'),
        'privileged-user-body': (source.replace('(let ((expanding nil))', '(let ((expanding t))'), 'handler-clause-case'),
    }
    rows = []
    for name, (text, refusal) in mutations.items():
        backend = out / (name + '.lisp')
        backend.write_text(text)
        selected = [r for r in conditions.SCOPE_REFUSALS if r[0] == refusal]
        require(len(selected) == 1, 'REFUSAL_CASE')
        try:
            compile_probe(evidence, out / name, backend,
                          {'h_signal': '(lambda (x) (signal x))'}, [], selected)
        except ValueError as error:
            require(str(error).startswith('NATIVE_COMPILE '), 'SPECIFIC_CONTROL_EXIT')
        else:
            raise AssertionError('SOURCE_SCOPE_MUTANT_ESCAPED ' + name)
        log = (out / name / 'compile.log').read_text()
        require('Unrefused source ' + refusal in log, 'SOURCE_SCOPE_ORACLE ' + name)
        rows.append(dict(name=name, status='REJECTED', oracle='Unrefused source ' + refusal))
    # Reproduce the concrete wrong answer, rather than only a changed admission.
    name = 'review-counterexample'
    sources = {'h_signal': '(lambda (x) (signal x))',
               'h_casebug': '(lambda (x) (case x (nil 1) (t 2)))'}
    cases = [dict(id='nil-case-key', function='h_casebug', args=['nil'], nodes=[],
                  bindings={}, capacity=4,
                  expected=dict(status='RETURN', values=[2], nodes=[], specials=[101,103,'unbound']))]
    compile_probe(evidence, out / name, out / 'unscoped-case.lisp', sources, cases, [])
    argv = ['/usr/local/bin/node', str(HERE / 'conditions.mjs'), str(out / name), str(out / (name + '.json'))]
    save(out / (name + '-command.json'), argv)
    with (out / (name + '.log')).open('w') as log:
        result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    text = (out / (name + '.log')).read_text()
    require(result.returncode != 0 and 'AssertionError' in text and 'nil-case-key' in text,
            'REVIEW_COUNTEREXAMPLE')
    require(read(out / name / 'native.json')[0]['values'] == [2], 'NATIVE_NIL_KEY')
    import re
    require(re.search(r'actual: \{[^}]*values: \[ 1 \]', text), 'TARGET_NIL_KEY')
    rows.append(dict(name=name, status='REJECTED', native=[2], target=[1],
                     oracle='literal native value comparison at nil-case-key'))
    save(out / 'controls.json', rows)
    return rows

if __name__ == '__main__':
    import sys
    print(run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
