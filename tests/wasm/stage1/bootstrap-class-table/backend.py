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
    old="    (cond ((and *b-cpl-conditions* (eq name 'gethash))"
    assert text.count(old)==1
    return text.replace(old,"""    (cond ((and *b-cpl-conditions* (eq name 'ccl::puthash))
           (b-call (bootstrap-constant 'ccl::%wasm-class-puthash) (list forms nil)))
          ((and *b-cpl-conditions* (eq name 'gethash))""")

def source_files(root):
    name='level-0/WASM32/w32-prims.lisp'
    text=(ROOT/name).read_text()
    old=""";;; The callable entry and the compiler's direct-call path share one protocol.
(defun signal (condition &rest arguments)
  (declare (dynamic-extent arguments))
  (apply #'%wasm-signal condition arguments))
"""
    assert text.count(old)==1
    result={name:text.replace(old,'')+'\n'+(HERE/'primitives.lisp').read_text()}
    name='level-1/l1-readloop.lisp';text=(ROOT/name).read_text()
    start=text.index('(defun signal (condition &rest args)')
    end=text.index('(defvar *error-print-circle*',start)
    original=text[start:end].rstrip()
    result[name]=text[:start]+"""#+wasm32-target
(defun signal (condition &rest args)
  (declare (dynamic-extent args))
  (apply #'%wasm-signal condition args))

#-wasm32-target
"""+original+'\n\n'+text[end:]
    return result

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
