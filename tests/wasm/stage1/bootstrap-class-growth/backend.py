"""Class-table publication through the accepted EQ service."""
from pathlib import Path
import importlib.util, hashlib, json
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('integrated',HERE.parent/'lap-primitives/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
BACKEND,ARCH=prior.BACKEND,prior.ARCH
arch,runtime_files=prior.arch,prior.runtime_files

def generate():
    text=prior.generate()
    needle="    (cond ((and *b-cpl-conditions* (eq name 'ccl::puthash))"
    assert text.count(needle)==1
    text=text.replace(needle,"""    (cond ((and *b-cpl-conditions* (eq name 'clrhash))
           (b-call (bootstrap-constant 'ccl::%wasm-class-clrhash) (list forms nil)))
          ((and *b-cpl-conditions* (eq name 'remhash))
           (b-call (bootstrap-constant 'ccl::%wasm-class-remhash) (list forms nil)))
          ((and *b-cpl-conditions* (eq name 'ccl::%wasm-eq-hash-key-p))
           (b-multiple (make-b-raw-code :text
             (bootstrap-operands forms
               (lambda (values)
                 (bootstrap-boolean
                   (b-wat \"(i32.and (i32.ne ~a (i32.const 243)) (i32.ne ~a (i32.const 251)))\"
                          (car values) (car values))))))))
          ((and *b-cpl-conditions* (eq name 'ccl::puthash))""")
    needle='(ccl::%make-uvector (or (bootstrap-allocate-bignum args)'
    assert text.count(needle)==1
    text=text.replace(needle,'(ccl::%make-uvector (or (bootstrap-allocate-eq-vector args) (bootstrap-allocate-bignum args)')
    for name, early in (
        ('b-implicit-runtime', '(when *b-cpl-conditions* (return-from b-implicit-runtime (bootstrap-class-implicit-runtime)))'),
        ('b-condition-runtime', '(when *b-cpl-conditions* (return-from b-condition-runtime (b-handler-runtime)))')):
        needle='(defun '+name+' ()\n'
        assert text.count(needle)==1
        text=text.replace(needle,needle+' '+early+'\n')
    needle='(defun bootstrap-condition (mask values)\n'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'  (when *b-cpl-conditions* (return-from bootstrap-condition (bootstrap-class-condition mask values)))\n')
    needle='(defun bootstrap-error-call (forms)\n'
    assert text.count(needle)==1
    text=text.replace(needle,needle+"""  (when (and *b-cpl-conditions* (= (length forms) 2)
             (eql (ccl::acode-fixnum-form-p (first forms)) ccl::$xfunbnd))
    (return-from bootstrap-error-call
      (b-multiple (make-b-raw-code :text
        (bootstrap-operands (cdr forms)
          (lambda (values)
            (b-wat \"(call $implicit_error_details (i32.const 14) (local.get $top) ~a (i32.const 77825)) unreachable\"
                   (car values))))))))
""")
    return text+'\n'+(HERE/'allocator.lisp').read_text()+'\n'+(HERE/'implicit.lisp').read_text()

def source_files(root):
    name='level-0/WASM32/w32-prims.lisp'
    text=(ROOT/name).read_text()
    old=(HERE.parent/'bootstrap-class-table/primitives.lisp').read_text()
    assert text.count(old)==1
    return {name:text.replace(old,(HERE/'primitives.lisp').read_text())}

def proposal(source,target):
    result=prior.proposal(source,target)
    for name,text in {BACKEND:generate(),**source_files(source)}.items():
        p=target/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        rows=[x for x in result['added']+result['modified'] if x['path']==name]
        if rows:
            row=rows[0];row['after' if 'after' in row else 'sha256']=digest
        else:result['modified'].append(dict(path=name,before=hashlib.sha256((source/name).read_bytes()).hexdigest(),after=digest))
    (target/'unit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result
