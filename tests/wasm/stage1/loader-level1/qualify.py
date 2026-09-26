"""Native code, every existing reader profile, and the compiler corpus."""
from pathlib import Path
import sys
import subprocess
import product
import storage

c, HERE = product.c, product.HERE
SHARED = ('level-1/l1-boot-1.lisp', 'level-1/l1-boot-2.lisp', 'level-1/l1-init.lisp',
          'level-1/l1-utils.lisp')
COMPILER_CHANGES = ('CCL::TARGET-COMPILER-MODULES', 'CCL::TARGET-XLOAD-MODULES',
                    'CCL::TARGET-COMPILE-MODULES')


def run(kind, out):
    if kind == 'native':
        comparison = product.module('level1_comparison', HERE.parent / 'loader/comparison.py')
        def compiler(before, after, source_before, source_after):
            result = comparison.compare(before, after, source_before, source_after,
                                        'lib/compile-ccl.lisp', COMPILER_CHANGES)
            changes = result['declared_changes']['definitions']
            for side in ('before', 'after'):
                assert {r['name'] for r in changes if r['side'] == side} == set(COMPILER_CHANGES)
            return result
        return product.module('level1_r6', HERE.parent / 'loader/r6.py').run(
            out, product.sources, ['lib/compile-ccl.lisp', *SHARED],
            compiler_comparator=compiler, compiler_changes=COMPILER_CHANGES)
    if kind == 'readers':
        bodies = product.sources()
        before = {n: subprocess.check_output(['git', 'show', '3bf0b390:' + n],
                    cwd=c.ROOT, text=True) for n in SHARED}
        return product.module('level1_readers', HERE.parent / 'namespace-consumers/readers.py').run(
            out, lambda: {n: bodies[n] for n in SHARED}, baseline_sources=before)
    assert kind == 'corpus'
    return product.module('level1_corpus', HERE.parent / 'loader-chain/qualify.py').run(kind, out, product)


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    kind, out = sys.argv[1], Path(sys.argv[2]).resolve()
    with storage.lease([out]):
        run(kind, out)
    print(kind, 'PASS')
