"""Compare both shared files under every existing target reader."""
from pathlib import Path
import sys
import qualify
import product
import storage

c = product.c


def run(out):
    driver = product.module('definition_reader_forms', product.HERE.parent / 'namespace-consumers/readers.py')
    original = (c.ROOT / 'level-0/l0-float.lisp').read_text()
    prelude = next(form for form in driver.top_forms(original) if form.startswith('(eval-when'))
    assert prelude in product.sources()['level-0/l0-float.lisp']
    command = c.command
    def execute(argv, *args, **kwargs):
        path = out / 'readers.lisp'
        if path in argv:
            path.write_text('(in-package "CCL")\n' + prelude + '\n' + path.read_text())
        return command(argv, *args, **kwargs)
    c.command = execute
    try:
        result = qualify.run('readers', out)
        result['unchanged_float_prelude'] = c.digest(prelude)
        c.save(out / 'summary.json', result)
        return result
    finally:
        c.command = command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        result = run(Path(sys.argv[1]).resolve())
        print({k: result[k] for k in ('status', 'files', 'profiles', 'comparisons')})
