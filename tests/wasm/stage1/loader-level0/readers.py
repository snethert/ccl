"""Existing-target reader proof for the package lookup branch."""
from pathlib import Path
import importlib.util
import subprocess
import sys
from types import SimpleNamespace
import product
import storage

HERE = Path(__file__).resolve().parent
c = product.c


def run(out, mutant=False):
    name = 'level-0/nfasload.lisp'
    before = (c.ROOT / name).read_text()
    after = product.sources()[name]
    start, end = '(defun %find-pkg ', '\n(defun pkg-arg '
    assert before[:before.index(start)] == after[:after.index(start)]
    assert before[before.index(end):] == after[after.index(end):]
    if mutant:
        assert after.count('#+wasm32-target progn') == 1
        after = after.replace('#+wasm32-target progn', 'progn')
    spec = importlib.util.spec_from_file_location('package_readers', HERE.parent / 'namespace-consumers/readers.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.proposal = SimpleNamespace(sources=lambda: {name: after})
    command = c.command
    def compare(argv, *args, **kwargs):
        path = out / 'readers.lisp'
        if path in argv:
            text = path.read_text()
            a = text.index('(defun reader-forms ')
            b = text.index('\n(let ((rows nil))', a)
            # Later native FASL tables contain read-time constants from their
            # compile environment. The complete prefix through the only edited
            # function is reader-compared; the suffix is byte-identical above.
            text = text[:a] + '''(defun reader-forms (path)
  (let ((*package* (find-package :ccl)) (*read-eval* t))
    (with-open-file (s path)
      (loop for form = (read s nil :eof) until (eq form :eof)
            collect form
            do (when (and (consp form) (eq (car form) 'in-package))
                 (setq *package* (find-package (second form))))
            until (and (consp form) (eq (car form) 'defun)
                       (eq (second form) '%find-pkg))))))
''' + text[b:]
            path.write_text(text)
        return command(argv, *args, **kwargs)
    c.command = compare
    try:
        result = driver.run(out)
    finally:
        c.command = command
    result['byte_identical_outside_changed_function'] = True
    result['scope'] = 'complete reader prefix through %FIND-PKG; unchanged suffix by byte identity'
    c.save(out / 'summary.json', result)
    return result


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        print(run(out / 'positive')['status'])
        try:
            run(out / 'mutant', True)
        except subprocess.CalledProcessError:
            assert 'Existing-target reader changed:' in (out / 'mutant/run.log').read_text()
            c.save(out / 'mutant.json', dict(status='KILLED', omission='Wasm reader guard'))
        else:
            raise AssertionError('reader mutant survived')
