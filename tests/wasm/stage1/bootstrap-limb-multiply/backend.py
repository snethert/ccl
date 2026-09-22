"""Select CCL's Lisp multiplication loop and supply its target LAP entries."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('digit_backend', HERE.parent / 'bootstrap-numeric-dispatch/backend.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
BACKEND, ARCH, PACKET, CLASSES = prior.BACKEND, prior.ARCH, prior.PACKET, prior.CLASSES
arch, runtime_files = prior.arch, prior.runtime_files

def generate():
    text = prior.generate()
    marker = "    (cond ((eq name 'ccl::%wasm-current-function)"
    assert text.count(marker) == 1
    return text.replace(marker, "    (cond ((member name '(ccl::%double-float-sign ccl::%short-float-sign))\n           (bootstrap-float-sign name forms))\n          ((eq name 'ccl::%wasm-current-function)") + "\n" + (HERE / "float-sign.lisp").read_text()

def source_files(root):
    result = prior.source_files(root)
    name = 'level-0/WASM32/w32-prims.lisp'
    result[name] += '\n' + (HERE / 'multiply.lisp').read_text()
    name = 'level-0/l0-bignum32.lisp'
    source = result.get(name, (root / name).read_text())
    old = '#+(or x8632-target arm-target)'
    assert source.count(old) == 1
    source = source.replace(old, '#+(or x8632-target arm-target wasm32-target)')
    start = '(let* ((ubytes (* len-a 4))'
    end = '(%copy-ptr-to-ivector rptr 0 res 0 rbytes)))'
    assert source.count(start) == source.count(end) == 1
    source = source.replace(start, '#-wasm32-target\n                 ' + start)
    result[name] = source.replace(end, end + '\n                 #+wasm32-target (error "GMP is unavailable on this target.")')
    return result

def proposal(src, out):
    origin = prior.prior.prior.prior
    origin.generate = generate
    origin.source_files = source_files
    return origin.proposal(src, out)
