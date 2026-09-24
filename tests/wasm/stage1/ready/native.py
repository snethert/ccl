"""R6/R6a for the READY compiler proposal; existing source allowances unchanged."""
from pathlib import Path
import importlib.util
import shutil
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
spec=importlib.util.spec_from_file_location('ready_compiler',HERE/'compiler.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
import build


def run(out):
    compiler.install();out.mkdir(parents=True,exist_ok=True)
    prepared=out/'prepared';prepared.mkdir()
    build.prepare(c.PARENT,prepared)
    proposed=prepared/'compiled/proposal'
    spec=importlib.util.spec_from_file_location('ready_native_driver',HERE.parent/'bootstrap-generic-dispatch/native.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    driver=native.driver
    for pair in [('level-1/l1-readloop.lisp','l1-fasls/l1-readloop.dx64fsl'),
                 ('level-0/l0-aprims.lisp','level-0/l0-aprims.dx64fsl'),
                 ('level-0/l0-misc.lisp','level-0/l0-misc.dx64fsl')]:
        if pair not in driver.SOURCE_PAIRS:driver.SOURCE_PAIRS.append(pair)
    driver.EXPECTED=['bin/systems.dx64fsl','bin/compile-ccl.dx64fsl']+[p[1] for p in driver.SOURCE_PAIRS]
    def proposal(source,destination):
        shutil.copytree(proposed,destination)
        return c.read(destination/'unit.json')
    driver.proposal=proposal
    c.save(out/'proposal-identity.json',c.inventory(proposed/'files'))
    return driver.run(c.STORE/'macos-u1-inputs',c.KERNEL,out/'work',out/'results',
                      c.STORE/'2026-09-16-stage1-1a-r2/native')


if __name__=='__main__':
    sys.setrecursionlimit(10000)
    with storage.lease([Path(sys.argv[1])]):
        raise SystemExit(run(Path(sys.argv[1])))
