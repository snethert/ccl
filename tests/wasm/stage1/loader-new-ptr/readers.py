"""Read both native-boundary files under all existing target profiles."""
from pathlib import Path
import sys
import qualify
import product
import storage

c = product.c


def run(out):
    # l0-bignum32's #. expressions use its own unchanged DIGIT-SIZE constant.
    # The generic reader comparator does not evaluate EVAL-WHEN forms.
    for body in ((c.ROOT / 'level-0/l0-bignum32.lisp').read_text(),
                 product.sources()['level-0/l0-bignum32.lisp']):
        assert body.count('(defconstant digit-size 32)') == 1
    command = c.command
    def execute(argv, *args, **kwargs):
        path = out / 'readers.lisp'
        if path in argv:
            path.write_text('(in-package "CCL")\n(defconstant digit-size 32)\n' + path.read_text())
        return command(argv, *args, **kwargs)
    c.command = execute
    try:
        return qualify.run('readers', out)
    finally:
        c.command = command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        print(run(Path(sys.argv[1]).resolve()))
