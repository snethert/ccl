"""R6/R6a for the final class/CPL compiler proposal in pristine U1."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backend

spec = importlib.util.spec_from_file_location('cpl_native', HERE.parent / 'bootstrap-generic-dispatch/native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
native.driver.proposal = backend.proposal
pair = ('level-1/l1-readloop.lisp', 'l1-fasls/l1-readloop.dx64fsl')
if pair not in native.driver.SOURCE_PAIRS:
    native.driver.SOURCE_PAIRS.append(pair)
native.driver.EXPECTED = ['bin/systems.dx64fsl', 'bin/compile-ccl.dx64fsl'] + [p[1] for p in native.driver.SOURCE_PAIRS]
sys.setrecursionlimit(10000)
output = Path(sys.argv[1]).resolve()
evidence = backend.ROOT.parent / 'ccl-evidence'
raise SystemExit(native.driver.run(evidence / 'macos-u1-inputs',
    evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
    output / 'work', output / 'native', evidence / '2026-09-16-stage1-1a-r2/native'))
