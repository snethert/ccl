"""Extend the retained GCD driver with original method-selection routines."""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'bootstrap-gcd'
sys.path.insert(0, str(HERE))
import backend
spec = importlib.util.spec_from_file_location('recipes_runner', HERE.parent / 'bootstrap-recipes/run.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
parent.backend = backend
parent.HERE = HERE.parent / 'bootstrap-lexpr-spread'
fallback = parent.fixture
search = [PRIOR, HERE.parent / 'bootstrap-clos-accessors', HERE.parent / 'bootstrap-limb-division',
          HERE.parent / 'bootstrap-lexpr-spread']
parent.fixture = lambda name: next((d / name for d in search if (d / name).is_file()), fallback(name))
copy = shutil.copy


def driver_copy(source, destination, *args, **kwargs):
    path = Path(destination)
    name = path.name
    if path.parent.name != 'driver':
        return copy(source, destination, *args, **kwargs)
    if name in ('new-inputs.lisp', 'execute.lisp', 'observers.lisp'):
        source = PRIOR / name
    if name == 'class-shapes.lisp':
        source = HERE.parent / 'bootstrap-lexpr-spread' / name
    result = copy(source, destination, *args, **kwargs)
    if name == 'compile.py':
        path.write_text(path.read_text().replace('timeout=120', 'timeout=300'))
    if name == 'new-inputs.lisp':
        text = path.read_text()
        needle = '(defun new-inputs (name)\n'
        assert text.count(needle) == 1
        path.write_text((HERE.parent / 'bootstrap-method-dispatch/inputs.lisp').read_text() + '\n' + (HERE / 'inputs.lisp').read_text() + '\n' + text.replace(needle, needle + '''  (multiple-value-bind (inputs covered) (generic-inputs name)
    (when covered (return-from new-inputs (values inputs t))))
'''))
    if name == 'arch-probes.lisp':
        text = path.read_text()
        needle = "  '((defun core-bignum-uvread"
        assert text.count(needle) == 1
        copy(HERE / 'methods.lisp', path.parent / 'methods.lisp')
        path.write_text(text.replace(needle, "  '(\n" + (HERE.parent / 'bootstrap-method-dispatch/probes.lisp').read_text() + '\n' + (HERE / 'probes.lisp').read_text() +
                                     '    (defun core-bignum-uvread'))
        text = path.read_text()
        text = text.replace('(defun arch-probe-forms ()', '(load (merge-pathnames "methods.lisp" *load-pathname*))\n\n(defun arch-probe-forms ()')
        text = text.replace("  '(\n", "  (append (generic-method-forms) (generic-protocol-forms) (generic-class-forms) (generic-condition-forms) '(\n", 1)
        path.write_text(text + ')\n')
    if name == 'execute.lisp':
        text = path.read_text()
        text = text.replace('(list ccl::%type-error-typespecs%)', '(list ccl::%type-error-typespecs% ccl::*lower-to-upper*)')
        needle = "(when (and (getf m :source-name) (symbolp (getf m :source-name))) (setf (gethash (getf m :source-name) by-name) m))"
        assert text.count(needle) == 1
        text = text.replace(needle, """(when (getf m :source-name)
        (let ((name (ccl::maybe-setf-function-name (getf m :source-name))))
          (setf (getf m :definition-name) (getf m :source-name)
                (getf m :source-name) name (gethash name by-name) m)))""")
        text = text.replace('(package-name (symbol-package name))', '(if (symbol-package name) (package-name (symbol-package name)) "")')
        text = text.replace('(defun core-json-value (x s)', '(load (merge-pathnames "graph.lisp" *load-pathname*))\n\n(defun core-json-value (x s)\n  (when (gethash x *generic-graphs*) (return-from core-json-value (generic-graph-json x s)))')
        copy(HERE / 'graph.lisp', path.parent / 'graph.lisp')
        text = text.replace('(defun core-copy-input (input)', '(defun core-copy-input (input)\n  (when (and (consp input) (gethash (car input) *generic-graphs*)) (return-from core-copy-input input))')
        # Keep the static-closure report honest. Requested dispatch callers
        # also exercise ordinary late-bound calls; unresolved names remain
        # empty symbol cells, never manufactured implementation stubs.
        needle = '(setq rows (nreverse rows))'
        assert text.count(needle) == 1
        text = text.replace(needle, '''(dolist (name '(core-generic-order core-generic-applicable core-generic-call core-generic-standard core-generic-select core-generic-updates core-generic-failure core-generic-resume core-generic-create core-generic-replace core-generic-builtin core-generic-arguments core-generic-empty-cycle core-generic-reader-dispatch))
      (let ((module (gethash name by-name)))
        (assert module)
        (multiple-value-bind (inputs covered) (core-inputs name)
          (assert covered)
          (unless (find name rows :key #'car)
            (push (list name module inputs) rows)))))
    ''' + needle)
        text = text.replace("(let ((needed (append '(", "(let ((needed (append '(core-generic-function-bits core-generic-set-function-bits core-generic-escape core-generic-cleanup core-generic-next-bad core-generic-reader-around ccl::%wasm-eql-specializer-reader core-default-class-precedence-list core-generic-optional core-generic-rest core-generic-class-of-list core-generic-class-of-function core-generic-class-of-instance core-generic-leaf core-generic-root core-generic-left core-generic-around core-generic-before core-generic-after core-generic-next-twice core-generic-next-args core-generic-key core-generic-pair core-generic-eql core-generic-pair-left core-generic-pair-right core-generic-empty core-default-add-method core-default-remove-method core-default-no-next-method core-default-no-applicable-method core-default-no-primary core-class-finalized-class core-class-finalized-std-class core-class-finalized-compile-time-class core-condition-p-t core-condition-p-condition ccl::funcallable-trampoline ")
        text = text.replace('(unless (gethash callee by-name) (error "Missing callee ~s from ~s" callee name))\n            (pushnew callee needed)',
                            '''(when (gethash callee by-name) (pushnew callee needed))''')
        path.write_text(text)
    if name == 'numeric-files.lisp':
        text = path.read_text()
        text += '\n(core-compile-file "ccl:level-1;l1-sort.lisp" t)\n(core-compile-file "ccl:level-1;l1-sort.lisp")\n'
        text += '\n(core-compile-file "ccl:level-0;l0-aprims.lisp" t)\n(core-compile-file "ccl:level-0;l0-aprims.lisp")\n(core-compile-file "ccl:lib;chars.lisp" t)\n(core-compile-file "ccl:lib;chars.lisp")\n'
        text += '\n(core-compile-file "ccl:lib;sequences.lisp" t)\n(core-compile-file "ccl:lib;sequences.lisp")\n'
        text += '\n(core-compile-file "ccl:level-1;l1-clos.lisp" t)\n(core-compile-file "ccl:level-1;l1-clos.lisp")\n'
        path.write_text(text)
    if name == 'compile.lisp':
        compiler_driver = path.parent / 'compile.py'
        compiler_driver.write_text(compiler_driver.read_text().replace('timeout=120', 'timeout=300'))
        text = path.read_text()
        needle = "(dolist (name '(core-dispatch-make core-dispatch-set))"
        assert text.count(needle) == 1
        path.write_text(text.replace(needle,
            "(dolist (name '(core-dispatch-make core-dispatch-set core-selection-first core-selection-second core-selection-default core-selection-generic core-generic-class-of-instance core-generic-class-of-function core-generic-prepare core-generic-select))"))
        for extra in ('numeric-files.lisp', 'arch-probes.lisp', 'new-inputs.lisp',
                      'clos-inputs.lisp', 'extra-controls.lisp'):
            driver_copy(parent.fixture(extra), path.parent / extra)
    return result


parent.shutil.copy = driver_copy
out = Path(sys.argv[1]).resolve()
parent.compile_corpus(out)
parent.stable_reader_diagnostics(out)
if '--compile-only' not in sys.argv:
    subprocess.run([sys.executable, HERE / 'execute.py', out], check=True)
