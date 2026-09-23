"""Condition construction and class lookup through CCL's Lisp machinery."""
from pathlib import Path
import importlib.util,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('integrated',HERE.parent/'lap-primitives/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
BACKEND,ARCH=prior.BACKEND,prior.ARCH
arch,runtime_files=prior.arch,prior.runtime_files

def generate():
    text=prior.generate()
    def replace(old,new):
        nonlocal text
        assert text.count(old)==1,old
        text=text.replace(old,new)
    start=text.index('(defun bootstrap-condition-typep (object type)')
    text=text[:start]+(HERE/'compiler.lisp').read_text()
    replace("          ((eq name 'make-condition)","          ((and (not *b-cpl-conditions*) (eq name 'make-condition))")
    replace("          ((eq name 'ccl::condition-arg)","          ((and (not *b-cpl-conditions*) (eq name 'ccl::condition-arg))")
    replace("((member name '(type-error-datum type-error-expected-type","((and (not *b-cpl-conditions*) (member name '(type-error-datum type-error-expected-type")
    replace("stream-error-stream file-error-pathname package-error-package))\n           (bootstrap-condition-reader","stream-error-stream file-error-pathname package-error-package)))\n           (bootstrap-condition-reader")
    replace("         (when *bootstrap-front-end*\n           (unless (and (null (third args)) (null (second (second args))))", """         (when (and *bootstrap-front-end* *b-cpl-conditions*)
           (return-from b-multiple
             (let ((callee (bootstrap-constant
                       (if (eq (first (ccl::acode-operands (first args))) 'error)
                         'ccl::%wasm-error 'ccl::%wasm-signal))))
               (if (third args)
                 (b-apply callee (second args) nil 0 (third args))
                 (b-call callee (second args))))))
         (when *bootstrap-front-end*
           (unless (and (null (third args)) (null (second (second args))))""")
    replace("    (cond ((and (eq name 'ccl::%function)","""    (cond ((and *b-cpl-conditions* (eq name 'gethash))
           (b-call (bootstrap-constant 'ccl::%wasm-class-gethash) (list forms nil)))
          ((and *b-cpl-conditions* (eq name 'coerce) (= (length forms) 2)
                (eq (bootstrap-immediate (second forms)) 'list))
           (b-call (bootstrap-constant 'ccl::coerce-to-list)
                   (list (list (first forms)) nil)))
          ((member name '(ccl::%wasm-signal-condition ccl::%wasm-error-condition))
           (unless (= (length forms) 1) (refuse :condition-signal-arity))
           (b-signal (first forms) (eq name 'ccl::%wasm-error-condition)))
          ((and *b-cpl-conditions* (eq name 'subtypep) (= (length forms) 2)
                (eq (bootstrap-immediate (second forms)) 'condition))
           (b-call (bootstrap-constant 'ccl::%wasm-condition-subtypep)
                   (list (list (first forms)) nil)))
          ((and (eq name 'ccl::%function)""")
    text=text.replace('(and *b-cpl-conditions* (bootstrap-condition-class-p type))',
                      "(and *b-cpl-conditions* (symbolp type) (not (member type '(nil t bit signed-byte unsigned-byte))) (not (assoc type *bootstrap-type-predicates*)) (find-class type nil))")
    return text

def source_files(root):
    result=prior.source_files(root)
    p='level-0/WASM32/w32-prims.lisp'
    result[p]=(ROOT/p).read_text()+'\n'+(HERE/'primitives.lisp').read_text()
    p='level-0/l0-def.lisp'
    text=(ROOT/p).read_text()
    old='(defun function-name (fun)\n'
    assert text.count(old)==1
    result[p]=text.replace(old,old+"  #+wasm32-target\n  (when (typep fun 'standard-generic-function)\n    (return-from function-name (%gf-name fun)))\n")
    p='level-1/l1-error-signal.lisp'
    text=(ROOT/p).read_text()
    old="""      (error (if (stringp condition)
               (make-condition 'simple-error :format-control condition :format-arguments args)
               condition))"""
    assert text.count(old)==1
    text=text.replace('  (%error condition args (%get-frame-ptr)))',"  #+wasm32-target (apply #'%wasm-error condition args)\n  #-wasm32-target (%error condition args (%get-frame-ptr)))")
    result[p]=text.replace(old,"""      (error (condition-arg condition (if (condition-p condition) nil args)
                            'simple-error))""")
    return result

def proposal(source,target):
    result=prior.proposal(source,target)
    values={BACKEND:generate(),**source_files(source)}
    for name,text in values.items():
        (target/'files'/name).write_text(text)
        digest=hashlib.sha256(text.encode()).hexdigest()
        rows=[row for row in result['added']+result['modified'] if row['path']==name]
        if rows:
            row=rows[0];row['after' if 'after' in row else 'sha256']=digest
        else:
            result['modified'].append(dict(path=name,before=hashlib.sha256((source/name).read_bytes()).hexdigest(),after=digest))
    (target/'unit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result
