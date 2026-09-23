"""Review 27f5bc02 using extra source forms and its unchanged native oracle.

Usage: logical-probe.py REVIEW_CHECKOUT BASELINE_OUTPUT NEW_OUTPUT --retry
The baseline is the output of lap-primitives/run.py at the reviewed commit.
Only a copied driver is changed; the compiler and runtime are unchanged.
--retry enables the compiler's existing allocation-retry mode for whole-file
library compilation. Without it the deliberately full heap reaches the
default profile's expected checked-6 allocation refusal.
"""
from pathlib import Path
import importlib.util
import random
import shutil
import subprocess
import sys

retry = '--retry' in sys.argv
root, baseline, out = map(lambda s: Path(s).resolve(), [s for s in sys.argv[1:] if s != '--retry'])
out.mkdir()
driver = out / 'driver'
shutil.copytree(baseline / 'driver', driver)
if retry:
    path = driver / 'compile.lisp'
    text = path.read_text()
    needle = '(in-package :wasm32-compiler)'
    assert text.count(needle) == 1
    path.write_text(text.replace(needle, needle + '\n(setq *b-allocation-retry* t)'))
rng = random.Random(2705922)
triples = [(0, -1, 7), (536870911, -536870912, 3)]
for i in range(38):
    triples.append(tuple(rng.getrandbits(rng.choice([29, 30, 61, 64, 127, 256, 1100]))
                         * rng.choice([-1, 1]) for _ in range(3)))
data = '(' + ' '.join('(' + ' '.join(map(str, row)) + ')' for row in triples) + ')'
forms = '''
    (defun core-review-logical (a b c)
      (values (logand a b c) (logior a b c) (logxor a b c)
              (logand a) (logior b) (logxor c) (logxor)))
    (defun core-review-logical-effects (a b c)
      (let ((order nil))
        (values
         (logand (progn (push 1 order) (core-collect) a)
                 (progn (push 2 order) (core-collect) b)
                 (progn (push 3 order) (core-collect) c))
         (logior (progn (push 4 order) (core-collect) a)
                 (progn (push 5 order) (core-collect) b)
                 (progn (push 6 order) (core-collect) c))
         (logxor (progn (push 7 order) (core-collect) a)
                 (progn (push 8 order) (core-collect) b)
                 (progn (push 9 order) (core-collect) c))
         order)))
    (defun core-retry-review-logical (force a b c)
      (declare (ignore force))
      (values (logand a b c) (logior a b c) (logxor a b c)))
    (defun core-review-logical-error (a b c)
      (values
       (handler-case (logand a b c)
         (type-error (condition) (type-error-datum condition)))
       (handler-case (logior a b c)
         (type-error (condition) (type-error-datum condition)))
       (handler-case (logxor a b c)
         (type-error (condition) (type-error-datum condition)))))
'''
with (driver / 'arch-probes.lisp').open('a') as stream:
    stream.write("\n(let ((previous (arch-probe-forms)))\n"
                 "  (setf (fdefinition 'arch-probe-forms)\n"
                 "        (lambda () (append previous '(" + forms + ")))))\n")
with (driver / 'new-inputs.lisp').open('a') as stream:
    stream.write('''
(let ((previous (fdefinition 'new-inputs)))
  (setf (fdefinition 'new-inputs)
        (lambda (name)
          (case name
            ((core-review-logical core-review-logical-effects)
             (values 'DATA t))
            (core-retry-review-logical
             (values (mapcar (lambda (row) (cons 1 row)) 'DATA) t))
            (core-review-logical-error
             (values '((:bad 2 3) (1 :bad 3) (1 2 :bad)
                       (1152921504606846976 :bad -1152921504606846977)
                       (1.5d0 2 3) (1 2 nil)) t))
            (t (funcall previous name))))))
'''.replace('DATA', data))

sys.path.insert(0, str(root / 'tests/wasm/stage1/lap-primitives'))
import backend
sys.path.insert(0, str(driver))
spec = importlib.util.spec_from_file_location('lap_probe_driver', driver / 'compile.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)
compiler.proposal = backend.proposal
compiler.run(root.parent / 'ccl-evidence', out / 'compiled', backend.generate())
subprocess.run([sys.executable, root / 'tests/wasm/stage1/lap-primitives/execute.py', out], check=True)
