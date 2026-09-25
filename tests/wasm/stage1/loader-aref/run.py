"""Compile and cross-load the complete array file with the real ordered prefix."""
from pathlib import Path
import hashlib
import shutil
import sys
import product
import identity
import storage

HERE = product.HERE
c = product.c


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    inputs = identity.drivers()
    c.save(out / 'proposal-inputs.json', inputs)
    driver = product.module('aref_prefix', HERE.parent / 'loader-locks/run.py')
    driver.product = product
    (out / 'array-boundary.lisp').write_text(product.sources()['level-0/WASM32/w32-lap.lisp'])
    command = c.command

    def execute(argv, log, env=None, **kwargs):
        if HERE.parent / 'loader-locks/ordered.lisp' in argv:
            result = command(argv, log, env, **kwargs)
            record = c.read(out / 'ordered.json')
            assert record['attempts'][1]['file'] == 'level-0/l0-array.lisp'
            assert record['attempts'][1]['failure'] is None
            source = Path(env['CCL_DEFAULT_DIRECTORY'])
            shutil.copyfile(source / 'level-0/l0-array.w32fsl', out / 'l0-array.w32fsl')
            (source / 'level-0/l0-array.lisp').unlink()
            return result
        if out / 'packages-produce.lisp' in argv:
            path = out / 'packages-produce.lisp'
            text = path.read_text()
            anchor = '("ccl:level-0;l0-array.lisp" ccl::%aref1 schar)'
            assert text.count(anchor) == 1
            text = text.replace(anchor, '')
            text = text.replace('characterp symbolp stringp listp', 'arrayp characterp symbolp stringp listp')
            text = text.replace('(\"ccl:level-1;l1-symhash.lisp\"',
                                '(\"ccl:lib;sequences.lisp\" make-string)\n                     (\"ccl:level-1;l1-symhash.lisp\"')
            anchor = '    (with-open-file (probes '
            assert text.count(anchor) == 1
            text = text.replace(anchor, (HERE / 'mutants.lisp').read_text() + '\n' + anchor)
            path.write_text(text)
            with (out / 'packages.lisp').open('a') as stream:
                stream.write((HERE / 'arrays.lisp').read_text())
        if out / 'load-prefix.lisp' in argv:
            path = out / 'load-prefix.lisp'
            text = path.read_text()
            anchor = '(list (concatenate \'string out "l0-aprims.w32fsl"))'
            assert text.count(anchor) == 1
            path.write_text(text.replace(anchor,
                '(list (concatenate \'string out "l0-aprims.w32fsl") '
                '(concatenate \'string out "l0-array.w32fsl"))'))
        return command(argv, log, env, **kwargs)

    c.command = execute
    try:
        driver.run(out)
    finally:
        c.command = command
    assert identity.drivers() == inputs, 'producer inputs changed during execution'


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
