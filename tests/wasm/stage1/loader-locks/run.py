"""Extend the saved-FASL prefix with the complete l0-aprims file."""
from pathlib import Path
import importlib.util
import shutil
import sys
import product
import storage

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'loader-level0'
c = product.c


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    return driver


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    driver = module('locks_prefix', PARENT / 'run.py')
    driver.unit = product
    # These are witness-selection changes, never production source rewriting.
    selection = (PARENT / 'packages-produce.lisp').read_text()
    selection = selection.replace('("ccl:level-0;l0-aprims.lisp" string)\n                     ', '')
    selection = selection.replace('"ccl:level-0;l0-misc.lisp" length list-length)',
        '"ccl:level-0;l0-misc.lisp" length list-length\n'
        '                      ccl::%wasm-rwlock-state ccl::%wasm-rwlock-acquisition\n'
        '                      ccl::%read-lock-rwlock-ptr ccl::%write-lock-rwlock-ptr\n'
        '                      ccl::%unlock-rwlock-ptr ccl::%promote-rwlock\n'
        '                      ccl::read-lock-rwlock ccl::write-lock-rwlock ccl::unlock-rwlock)')
    selection = selection.replace('ccl::fixnump)', 'ccl::fixnump simple-vector-p ccl::register-istruct-cell)')
    selection = selection.replace('"ccl:level-0;l0-symbol.lisp" symbol-name)',
        '"ccl:level-0;l0-symbol.lisp" symbol-name ccl::get-type-predicate ccl::set-type-predicate ccl::%symbol-bits)')
    selection = selection.replace('("ccl:level-1;l1-symhash.lisp"',
        '("ccl:level-1;l1-processes.lisp" ccl::read-write-lock-p\n'
        '                      ccl::lock-acquisition-status ccl::clear-lock-acquisition-status)\n'
        '                     ("ccl:level-1;l1-symhash.lisp"')
    anchor = '(write form :stream s) (terpri s)'
    assert selection.count(anchor) == 1
    selection = selection.replace(anchor, anchor + '''
                   (when (eq (second form) 'ccl::%wasm-rwlock-state)
                     (dolist (clause '((ccl::loader-rwlock-mutant-state
                                       (eq (zerop ccl::owner) (zerop ccl::depth)))
                                      (ccl::loader-rwlock-mutant-owner (typep ccl::owner 'fixnum))
                                      (ccl::loader-rwlock-mutant-depth (typep ccl::depth 'fixnum))))
                       (let ((mutant (subst t (second clause) (copy-tree form) :test #'equal)))
                         (assert (not (equal mutant form)))
                         (setf (second mutant) (first clause))
                         (write mutant :stream s) (terpri s))))''')
    (out / 'packages-produce.lisp').write_text(selection)
    (out / 'packages.lisp').write_text((PARENT / 'packages.lisp').read_text() + (HERE / 'locks.lisp').read_text())
    load = (PARENT / 'load-prefix.lisp').read_text()
    load = load.replace('(append fasls (mapcar', '(append fasls (list (concatenate \'string out "l0-aprims.w32fsl")) (mapcar')
    (out / 'load-prefix.lisp').write_text(load)
    command = c.command

    def execute(argv, log, env=None, **kwargs):
        argv = list(argv)
        if PARENT / 'ordered.lisp' in argv:
            argv[argv.index(PARENT / 'ordered.lisp')] = HERE / 'ordered.lisp'
            result = command(argv, log, env, **kwargs)
            record = c.read(out / 'ordered.json')
            assert record['attempts'][0]['failure'] is None, record
            source = Path(env['CCL_DEFAULT_DIRECTORY'])
            shutil.copyfile(source / 'level-0/l0-aprims.w32fsl', out / 'l0-aprims.w32fsl')
            (source / 'level-0/l0-aprims.lisp').unlink()
            return result
        if PARENT / 'packages-produce.lisp' in argv:
            argv[argv.index(PARENT / 'packages-produce.lisp')] = out / 'packages-produce.lisp'
            env = dict(env, LOADER_SOURCE=str(out) + '/')
        if PARENT / 'load-prefix.lisp' in argv:
            argv[argv.index(PARENT / 'load-prefix.lisp')] = out / 'load-prefix.lisp'
        return command(argv, log, env, **kwargs)

    c.command = execute
    try:
        driver.run(out)
    finally:
        c.command = command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
