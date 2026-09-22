"""R6/R6a on the final proposed backend and native-preserving source branches."""
import argparse,importlib.util,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import backend
sys.path.insert(1,str(HERE.parent/'bootstrap-admission'))
spec=importlib.util.spec_from_file_location('admission_native',HERE.parent/'bootstrap-admission/native.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.driver.proposal=backend.proposal
m.driver.SOURCE_PAIRS += [('level-1/l1-numbers.lisp','l1-fasls/l1-numbers.dx64fsl'),('level-0/l0-array.lisp','level-0/l0-array.dx64fsl')]
m.driver.EXPECTED=['bin/systems.dx64fsl','bin/compile-ccl.dx64fsl']+[p[1] for p in m.driver.SOURCE_PAIRS]
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','work','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence.resolve()
 raise SystemExit(m.driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),a.output.resolve(),e/'2026-09-16-stage1-1a-r2/native'))
