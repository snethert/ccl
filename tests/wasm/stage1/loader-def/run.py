"""Compile and cross-load the ordered function-definition file."""
from pathlib import Path
import shutil
import sys
import product
import storage

HERE = product.HERE
c = product.c
FILES = ('l0-def', 'l0-error', 'l0-float')


def run(out):
    driver = product.module('definition_prefix', HERE.parent / 'loader-new-ptr/run.py')
    driver.product = product
    driver.HERE = HERE.parent / 'loader-new-ptr'
    command = c.command

    def execute(argv, log, env=None, **kwargs):
        if HERE.parent / 'loader-locks/ordered.lisp' in argv:
            result = command(argv, log, env, **kwargs)
            record = c.read(out / 'ordered.json')
            source = Path(env['CCL_DEFAULT_DIRECTORY'])
            for name in FILES:
                row = next(r for r in record['attempts'] if r['file'] == 'level-0/' + name + '.lisp')
                assert row.get('fasl') and not row['failure'], row
                shutil.copyfile(source / row['fasl'], out / (name + '.w32fsl'))
                (source / row['file']).unlink()
            return result
        if out / 'packages-produce.lisp' in argv:
            path = out / 'packages-produce.lisp'
            text = path.read_text()
            text = text.replace('ccl::%symbol-bits)', 'ccl::%symbol-bits ccl::%global-macro-function)')
            text = text.replace('ccl::register-istruct-cell)',
                                'ccl::register-istruct-cell integerp compiled-function-p ccl::macptrp floatp ccl::double-float-p ccl::short-float-p ccl::bignump rationalp realp numberp)')
            anchor = '("ccl:lib;sequences.lisp" make-string)'
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor + '\n                     ("ccl:level-0;l0-hash.lisp" hash-table-p)'
                '\n                     ("ccl:level-1;l1-dcode.lisp" ccl::standard-generic-function-p)'
                '\n                     ("ccl:level-1;l1-utils.lisp" fdefinition symbol-function)')
            anchor = "                 (when (and (consp form) (eq (car form) 'defun)"
            assert text.count(anchor) == 1
            text = text.replace(anchor, '''                 ;; HASHENV defines the read-time constants used before HASH-TABLE-P.
                 ;; Preserve and evaluate the complete original prelude.
                 (when (and (equal (first group) "ccl:level-0;l0-hash.lisp")
                            (consp form) (eq (car form) 'eval-when))
                   (eval form)
                   (write form :stream s) (terpri s))
''' + anchor)
            assert text.count('(ccl:quit)') == 1
            text = text.replace('(ccl:quit)', (HERE / 'compiler-controls.lisp').read_text() + '\n(ccl:quit)')
            path.write_text(text)
            with (out / 'packages.lisp').open('a') as stream:
                stream.write((HERE / 'witnesses.lisp').read_text())
        if out / 'load-prefix.lisp' in argv:
            path = out / 'load-prefix.lisp'
            text = path.read_text()
            anchor = '(concatenate \'string out "l0-complex.w32fsl")'
            assert text.count(anchor) == 1
            extra = ' '.join('(concatenate \'string out "' + name + '.w32fsl")' for name in FILES)
            text = text.replace(anchor, anchor + ' ' + extra)
            path.write_text('(in-package \"CCL\")\n(setq *load-verbose* t)\n' + text)
        return command(argv, log, env, **kwargs)

    c.command = execute
    try:
        driver.run(out)
    finally:
        c.command = command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
