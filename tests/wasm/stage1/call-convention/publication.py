"""Corrupt metadata at its producer; compilation must refuse publication."""
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def run(boot, out):
    out.mkdir(parents=True)
    controls = []
    for kind, producer, mutation, refusal in [
        ('arity-shape', 'metadata-arity', '(subseq value 0 6)', 'CALLABLE-METADATA-POOL'),
        ('arity-version', 'metadata-arity', '(setf (svref value 0) 0) value', 'CALLABLE-METADATA-ARITY'),
        ('required-count', 'metadata-arity', '(incf (svref value 1)) value', 'CALLABLE-METADATA-ARITY'),
        ('debug-version', 'metadata-debug', '(setf (svref value 0) 0) value', 'CALLABLE-METADATA-ARITY'),
    ]:
        source = out/(kind+'.lisp')
        source.write_text(f'''(in-package "CCL")
(eval-when (:compile-toplevel)
  (let ((original (symbol-function 'wasm32-compiler::{producer})))
    (setf (symbol-function 'wasm32-compiler::{producer})
      (lambda (afunc)
        (let ((value (funcall original afunc))) {mutation})))))
(defun cc-publication-control () 0)
''')
        build = out/kind
        argv = [sys.executable, str(HERE.parent/'loader-target/build.py'), str(build),
                '--postimage='+str(boot), '--source='+str(source)]
        with (out/(kind+'.log')).open('w') as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode, kind
        assert refusal in (build/'compile.log').read_text(), kind
        assert not (build/'benchmark.w32bundle').exists(), kind
        controls.append(dict(kind=kind, status='CHECKED_REFUSAL', predicate=refusal))
        print(kind, 'CHECKED_REFUSAL', flush=True)
    (out/'publication.json').write_text(json.dumps(dict(status='PASS', controls=controls), indent=2)+'\n')


if __name__ == '__main__':
    run(*[Path(p).resolve() for p in sys.argv[1:3]])
