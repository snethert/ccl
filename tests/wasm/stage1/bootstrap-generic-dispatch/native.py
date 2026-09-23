"""Qualify the final dispatch proposal, including its CCL source branches."""
from pathlib import Path
import argparse
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backend
spec = importlib.util.spec_from_file_location('prior_native', HERE.parent / 'bootstrap-gcd/native.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
driver = prior.m.driver
# FASL EPUSH reserves the containing object before decoding its fields. Native
# LABELS functions can refer back to an enclosing, still-reserved function.
# Preserve that edge by its enclosing-object depth rather than making a Python
# cycle or mistaking it for an invalid forward reference.
import native_compare
class RecursiveCompilerFasl(native_compare.CompilerFasl):
    def expr(self, depth=0):
        if self.pos < len(self.data) and self.data[self.pos] == 25:
            start = self.pos
            self.byte()
            index = self.count()
            assert index < len(self.refs), 'FASL_REFERENCE'
            if self.refs[index] is None:
                self.ops.append(dict(offset=start, opcode=25, epush=False))
                return {'enclosing-reference': sum(v is None for v in self.refs[index:]) - 1}
            self.pos = start
        return super().expr(depth)
native_compare.CompilerFasl = RecursiveCompilerFasl
for name in ('l1-dcode', 'l1-clos'):
    pair = (f'level-1/{name}.lisp', f'l1-fasls/{name}.dx64fsl')
    if pair not in driver.SOURCE_PAIRS:
        driver.SOURCE_PAIRS.append(pair)
driver.EXPECTED = ['bin/systems.dx64fsl', 'bin/compile-ccl.dx64fsl'] + [p[1] for p in driver.SOURCE_PAIRS]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('evidence', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    raise SystemExit(driver.run(evidence / 'macos-u1-inputs',
        evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
        args.work.resolve(), args.output.resolve(),
        evidence / '2026-09-16-stage1-1a-r2/native'))
