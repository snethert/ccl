"""Supply the digit division LAP entries used by CCL's original bignum code."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('multiply_backend',HERE.parent/'bootstrap-limb-multiply/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
BACKEND,ARCH,PACKET,CLASSES=prior.BACKEND,prior.ARCH,prior.PACKET,prior.CLASSES
generate,arch,runtime_files=prior.generate,prior.arch,prior.runtime_files

def source_files(root):
    files=prior.source_files(root)
    files['level-0/WASM32/w32-prims.lisp']+='\n'+(HERE/'division.lisp').read_text()
    name='level-0/l0-bignum32.lisp'
    old='(return-from bignum-truncate (values 0 x1))'
    assert files[name].count(old)==1
    files[name]=files[name].replace(old,'(return-from bignum-truncate #+wasm32-target (if no-rem 0 (values 0 x1)) #-wasm32-target (values 0 x1))')
    return files

def proposal(src,out):
    origin=prior.prior.prior.prior.prior
    origin.generate=generate
    origin.source_files=source_files
    return origin.proposal(src,out)
