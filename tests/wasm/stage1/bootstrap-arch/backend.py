"""Arch macro proposal over the reviewed closure compiler; no shared edits."""
import hashlib, importlib.util, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('arch_parent',HERE.parent/'bootstrap-recipes/backend.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
BACKEND,ARCH=parent.BACKEND,parent.ARCH
PACKET=parent.PACKET

def generate():
    text=parent.generate()
    marker='(defun bootstrap-make-vector (forms)'
    assert text.count(marker)==1
    text=text.replace(marker,(HERE/'float-allocation.lisp').read_text()+marker)
    old='(ccl::%make-uvector (bootstrap-make-vector args))'
    assert text.count(old)==1
    text=text.replace(old,'(ccl::%make-uvector (or (bootstrap-allocate-float args)\n                                 (bootstrap-make-vector args)))')
    old='      ((ccl::%single-float ccl::%double-float)'
    assert text.count(old)==1
    text=text.replace(old,'      ((ccl::%setf-double-float ccl::%setf-short-float)\n       (bootstrap-float-store args))\n'+old)
    old="    (cond ((eq name 'ccl::%wasm-float-store)"
    assert text.count(old)==1
    new="""    (cond ((member name '(ccl::%copy-double-float ccl::%copy-short-float
                          ccl::%int-to-dfloat ccl::%int-to-sfloat!))
           (unless (= (length forms) 2) (refuse :bootstrap-float-store-arity))
           (b-multiple
            (make-b-raw-code :text
              (bootstrap-operands forms
                (lambda (values)
                  (let* ((source (make-b-raw-code :text (first values)))
                         (destination (make-b-raw-code :text (second values)))
                         (conversion (member name '(ccl::%int-to-dfloat ccl::%int-to-sfloat!))))
                    (when conversion
                      (setq source
                            (make-b-raw-code :text
                              (b-wat "~a ~a"
                                     (b-condition (b-wat "(i32.and ~a (i32.const 3))" (first values)) 5)
                                     (bootstrap-primary
                                      (b-float-call (if (eq name 'ccl::%int-to-dfloat)
                                                     '%float-double '%float-single)
                                                    (list source (bootstrap-constant 0))))))))
                    (bootstrap-float-store (list destination source))))))))
          ((eq name 'ccl::%wasm-float-store)"""
    return text.replace(old,new)

def source_files(src):
    spec=importlib.util.spec_from_file_location('arch_sources',HERE/'sources.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return {**parent.source_files(src),**module.derive()}

def proposal(src,out):
    manifest=parent.proposal(src,out)
    changes={BACKEND:generate(), ARCH:(ROOT/ARCH).read_text()+'\n'+(HERE/'arch-macros.lisp').read_text(), **source_files(src)}
    known={r['path'] for r in manifest['added']+manifest['modified']}
    for name,text in changes.items():
        if name not in known:
            manifest['modified'].append(dict(path=name,before=hashlib.sha256((src/name).read_bytes()).hexdigest(),after=''))
            (out/'files'/name).parent.mkdir(parents=True,exist_ok=True)
    for row in manifest['added']+manifest['modified']:
        if row['path'] in changes:
            p=out/'files'/row['path'];p.write_text(changes[row['path']])
            row['sha256' if 'sha256' in row else 'after']=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

runtime_files=parent.runtime_files
