"""Build whole production files in order, then cross-load only their FASLs."""
from pathlib import Path
import shutil
import sys
import product
import storage

HERE = product.HERE
PARENT = HERE.parent / 'loader-aref'
c = product.c
FILES = ('l0-bignum32', 'l0-bignum64', 'l0-cfm-support', 'l0-complex')


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'bignum-boundary.lisp').write_text(product.sources()['level-0/l0-bignum32.lisp'])
    driver = product.module('ptr_prefix', PARENT / 'run.py')
    driver.HERE = PARENT
    driver.product = product
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
            with (out / 'packages.lisp').open('a') as stream:
                stream.write((HERE / 'witnesses.lisp').read_text())
            path = out / 'packages-produce.lisp'
            text = path.read_text()
            text = text.replace('arrayp characterp symbolp stringp listp',
                                'arrayp characterp symbolp stringp ccl::base-string-p listp')
            anchor = '         (dolist (group'
            assert text.count(anchor) == 1
            text = text.replace(anchor, '''         (with-open-file (input (concatenate 'string out "bignum-boundary.lisp"))
           (loop for form = (read input nil :end) until (eq form :end) do
             (when (and (consp form) (eq (car form) 'eval-when))
               (write form :stream s) (terpri s) (return))))
''' + anchor)
            anchor = '("ccl:lib;sequences.lisp" make-string)'
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor + '''
                     ("ccl:level-0;l0-numbers.lisp"
                      ccl::logand-2 ccl::logior-2 ccl::logxor-2 lognot minusp oddp evenp
                      truncate ccl::truncate-no-rem ccl::%unary-truncate ccl::xform-truncate
                      ccl::+-2 ccl::+-2-into ccl::<-2 ccl::>-2 ccl::%negate
                      ccl::=-2 ccl::>=-2 ccl::<=-2)
                     ("ccl:level-1;l1-numbers.lisp" + max min ccl::max-2 ccl::min-2)''')
            anchor = "                 (when (and (consp form) (eq (car form) 'defun)"
            assert text.count(anchor) == 1
            text = text.replace(anchor, '''                 ;; Keep the complete numeric file's macro/require prelude.
                 ;; These original forms establish the compilation environment
                 ;; of the selected complete definitions; no body is rewritten.
                 (when (and (member (first group)
                                    '("ccl:level-0;l0-numbers.lisp" "ccl:level-1;l1-numbers.lisp")
                                    :test #'equal)
                            (consp form) (eq (car form) 'eval-when))
                   (write form :stream s) (terpri s))
''' + anchor)
            assert text.count('(ccl:quit)') == 1
            path.write_text(text.replace('(ccl:quit)',
                (HERE / 'literal-controls.lisp').read_text() + '\n(ccl:quit)'))
        if out / 'load-prefix.lisp' in argv:
            path = out / 'load-prefix.lisp'
            text = path.read_text()
            anchor = '(concatenate \'string out "l0-array.w32fsl")'
            assert text.count(anchor) == 1
            extra = ' '.join('(concatenate \'string out "' + name + '.w32fsl")' for name in FILES)
            path.write_text(text.replace(anchor, anchor + ' ' + extra))
        return command(argv, log, env, **kwargs)

    c.command = execute
    try:
        driver.run(out)
    finally:
        c.command = command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
