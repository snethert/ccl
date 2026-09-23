"""A class/CPL handler path over the integrated compiler; legacy mode stays put."""
from pathlib import Path
import importlib.util
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('integrated', HERE.parent / 'lap-primitives/backend.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
BACKEND, ARCH = prior.BACKEND, prior.ARCH
arch, runtime_files, source_files = prior.arch, prior.runtime_files, prior.source_files


def generate():
    text = prior.generate()
    def replace(old, new):
        nonlocal text
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    replace('(defvar *b-condition-used* nil)',
            '(defvar *b-condition-used* nil)\n(defvar *b-cpl-conditions* nil)')
    replace('(b-condition-mask (car clause)))))\n      (if (eq expander bits)',
            '(if *b-cpl-conditions*\n                (bootstrap-condition-class (car clause))\n                (b-condition-mask (car clause))))))\n      (if (eq expander bits)')
    replace('(write-string (b-wat "(i32.store offset=8 ~a ~a) (drop (call $condition_mask ~a))" root (b-scalar form) condition) s)',
            '''(write-string (b-wat "(i32.store offset=8 ~a ~a) ~a" root (b-scalar form)
              (if *b-cpl-conditions*
                (b-condition (b-wat "(i32.eqz ~a)"
                  (bootstrap-condition-typep condition (bootstrap-symbol 'condition))) 5)
                (b-wat "(drop (call $condition_mask ~a))" condition))) s)''')
    replace('''(b-wat "(if (i32.and (call $condition_mask ~a) ~a) (then"
                        condition
                        (if *bootstrap-front-end*''',
            '''(b-wat "(if ~a (then"
                      (if *b-cpl-conditions*
                        (bootstrap-condition-typep condition
                          (b-wat "(i32.load offset=4 (call $handler_cons ~a))" handlers))
                        (b-wat "(i32.and (call $condition_mask ~a) ~a)"
                        condition
                        (if *bootstrap-front-end*''')
    replace('''(b-wat "(i32.shr_u (i32.load offset=4 (call $handler_cons ~a)) (i32.const 2))" handlers))) s)''',
            '''(b-wat "(i32.shr_u (i32.load offset=4 (call $handler_cons ~a)) (i32.const 2))" handlers))))) s)''')
    replace('(let ((s (prior-float-b-condition-runtime)))',
            '''(let ((s (concatenate 'string (prior-float-b-condition-runtime)
              (if *b-cpl-conditions* (bootstrap-condition-class-runtime) ""))))''')
    # TYPEP and REQUIRE-TYPE share the same ordinary class predicate as handlers.
    replace("(cond ((symbolp type) (or (member type '(nil t bit signed-byte unsigned-byte))",
            "(cond ((symbolp type) (or (and *b-cpl-conditions* (bootstrap-condition-class-p type)) (member type '(nil t bit signed-byte unsigned-byte))")
    replace('''    (cond ((null type) "(i32.const 0)")''',
            '''    (cond ((and *b-cpl-conditions* (bootstrap-condition-class-p type))
           (bootstrap-condition-typep value (bootstrap-symbol type)))
          ((null type) "(i32.const 0)")''')
    return text + '\n' + (HERE / 'compiler.lisp').read_text()


def proposal(source, target):
    result = prior.proposal(source, target)
    path = target / 'files' / BACKEND
    path.write_text(generate())
    for row in result['added'] + result['modified']:
        if row['path'] == BACKEND:
            row['after' if 'after' in row else 'sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (target / 'unit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result
