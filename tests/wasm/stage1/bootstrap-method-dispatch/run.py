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
    if name == 'new-inputs.lisp':
        text = path.read_text()
        needle = '(defun new-inputs (name)\n'
        assert text.count(needle) == 1
        path.write_text((HERE / 'inputs.lisp').read_text() + '\n' + text.replace(needle, needle + '''  (multiple-value-bind (inputs covered) (selection-inputs name)
    (when covered (return-from new-inputs (values inputs t))))
'''))
    if name == 'arch-probes.lisp':
        text = path.read_text()
        needle = "  '((defun core-bignum-uvread"
        assert text.count(needle) == 1
        path.write_text(text.replace(needle, "  '(\n" + (HERE / 'probes.lisp').read_text() +
                                     '    (defun core-bignum-uvread'))
    if name == 'compile.lisp':
        text = path.read_text()
        needle = "(dolist (name '(core-dispatch-make core-dispatch-set))"
        assert text.count(needle) == 1
        path.write_text(text.replace(needle,
            "(dolist (name '(core-dispatch-make core-dispatch-set core-selection-first core-selection-second core-selection-default core-selection-generic))"))
        for extra in ('numeric-files.lisp', 'arch-probes.lisp', 'new-inputs.lisp',
                      'clos-inputs.lisp', 'extra-controls.lisp'):
            driver_copy(parent.fixture(extra), path.parent / extra)
    return result


parent.shutil.copy = driver_copy
out = Path(sys.argv[1]).resolve()
parent.compile_corpus(out)
parent.stable_reader_diagnostics(out)
subprocess.run([sys.executable, PRIOR / 'execute.py', out], check=True)
