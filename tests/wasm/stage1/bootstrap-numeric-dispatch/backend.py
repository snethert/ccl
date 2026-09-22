"""Numeric LAP replacements and callable dispatch over the pending bootstrap compiler."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('spread_backend',HERE.parent/'bootstrap-lexpr-spread/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
BACKEND=prior.BACKEND;ARCH=prior.ARCH;PACKET=prior.PACKET;CLASSES=prior.CLASSES
arch=prior.arch;runtime_files=prior.runtime_files

def generate():
    s=prior.generate()
    marker="    (cond ((eq name 'ccl::%wasm-function-keyvect)"
    assert s.count(marker)==1
    s=s.replace(marker,"    (cond ((eq name 'ccl::%wasm-current-function)\n           (unless (null forms) (refuse :current-function-arity))\n           (b-multiple (make-b-raw-code :text \"(i32.load offset=40 (local.get $context))\")))\n          ((member name '(ccl::%wasm-bignum-half-ref ccl::%wasm-bignum-set ccl::%wasm-bignum-length-set ccl::%copy-ivector-to-ivector))\n           (b-multiple (make-b-raw-code :text (bootstrap-bignum-call name forms))))\n          ((eq name 'ccl::%wasm-function-keyvect)")
    marker='(ccl::%make-uvector (or (bootstrap-allocate-float args)'
    assert s.count(marker)==1
    s=s.replace(marker,'(ccl::%make-uvector (or (bootstrap-allocate-bignum args) (bootstrap-allocate-float args)')
    old="          ((eq name 'ldb) (bootstrap-ldb forms))"
    assert s.count(old)==1
    s=s.replace(old,"          ((and (eq name 'truncate) (= (length forms) 2)\n                (every (lambda (form) (ccl::acode-form-typep form 'fixnum t)) forms))\n           (b-integer-call '%integer-truncate forms))\n"+old)
    return s+'\n'+(HERE/'bignum.lisp').read_text()

def source_files(root):
    result=prior.source_files(root)
    name='level-0/WASM32/w32-prims.lisp'
    result[name]=result[name]+'\n'+(HERE/'w32-bignum.lisp').read_text()+'\n'+(HERE/'w32-dispatch.lisp').read_text()
    return result

def proposal(src,out):
    # The proposal builder lives at the base of the retained derivation chain.
    origin=prior.prior.prior
    origin.generate=generate;origin.source_files=source_files
    return origin.proposal(src,out)
