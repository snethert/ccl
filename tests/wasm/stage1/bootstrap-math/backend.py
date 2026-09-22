"""Next execution proposal over the accepted audit-153 source."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PACKET=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-admission-r1/execution/compiled/proposal'
BACKEND='compiler/WASM32/wasm32-backend.lisp'
ARCH='compiler/WASM32/wasm32-arch.lisp'

def generate():
    text=(ROOT/BACKEND).read_text()
    anchor='(defun bootstrap-operator (ir)'
    assert text.count(anchor)==1
    text=text.replace(anchor,(HERE/'numeric.lisp').read_text()+'\n'+anchor)
    anchor='    (case op\n'
    start=text.index('(defun bootstrap-operator (ir)')
    text=text[:start]+text[start:].replace(anchor,anchor+(HERE/'numeric-cases.lisp').read_text(),1)
    names = ['%libm-' + n + w for n in ('expt','sin','cos','acos','asin','cosh','log','tan','atan','atan2','exp','sinh','tanh') for w in ('64','32')]
    a=text.index('(defun b-float-call');b=text.index('(defun b-float-runtime',a)
    call=text[a:b]
    call=call.replace('%float-single %float-double))', '%float-single %float-double '+' '.join(names)+'))')
    operations = ' '.join(n for n in ('expt','sin','cos','acos','asin','cosh','log','tan','atan','atan','exp','sinh','tanh') for _ in (0,1))
    call=call.replace('> float float))))', "> float float "+operations+"))) (unary (and (>= op 10) (not (member op '(12 13 30 31))))))")
    # Leave the LET binding's test intact; generalize the two operand-list tests.
    call=call.replace('(if (>= op 10)', '(if unary')
    text=text[:a]+call+text[b:]
    anchor="    (cond ((eq name 'ldb)"
    branch="""    (cond ((eq name 'ccl::%wasm-float-store)
           (b-multiple (make-b-raw-code :text (bootstrap-float-store forms))))
          ((eq name 'ccl::%wasm-float-transcend)
           (let ((op (ccl::acode-fixnum-form-p (car forms))))
             (unless (and op (<= 12 op 37) (= (length forms) 3))
               (refuse :bootstrap-transcend-operation))
             (b-float-call (nth (- op 12) '(%s)) (cdr forms))))
          ((eq name 'ldb)""".replace("%s", ' '.join(names))
    assert text.count(anchor)==1
    text=text.replace(anchor,branch)
    text=text.replace("((member name '(logand logior logxor)) (bootstrap-logical-call name forms))",
                      "((member name '(logand logior logxor)) (or (bootstrap-word-logical name forms) (bootstrap-logical-call name forms)))")
    return text

def source_files(src):
    manifest=json.loads((PACKET/'unit.json').read_text())
    result = {r['path']:(ROOT/r['path']).read_text() for r in manifest['added']+manifest['modified'] if r['path'].startswith(('level-0/','level-1/'))}
    import importlib.util
    spec=importlib.util.spec_from_file_location('math_sources',HERE/'math-sources.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result['level-1/l1-numbers.lisp']=module.derive()
    array=(ROOT/'level-0/l0-array.lisp').read_text()
    anchor='      #+arm-target\n      (svref arm::*immheader-array-types*'
    assert array.count(anchor)==1
    branch="""      #+wasm32-target
      (svref '#(short-float (unsigned-byte 32) (signed-byte 32) fixnum
                character (unsigned-byte 8) (signed-byte 8)
                (unsigned-byte 16) (signed-byte 16) double-float
                (complex single-float) (complex double-float) bit)
             (ash (the fixnum (- subtag target::min-cl-ivector-subtag)) -3))
"""
    result['level-0/l0-array.lisp']=array.replace(anchor,branch+anchor)
    return result

def proposal(src,out):
    shutil.copytree(PACKET,out)
    manifest=json.loads((out/'unit.json').read_text())
    changed={BACKEND:generate(),**source_files(src)}
    for path in ('level-1/l1-numbers.lisp','level-0/l0-array.lisp'):
        if not any(r['path']==path for r in manifest['modified']):
            manifest['modified'].append(dict(path=path,before=hashlib.sha256((src/path).read_bytes()).hexdigest()))
    for row in manifest['added']+manifest['modified']:
        p=out/'files'/row['path'];p.write_text(changed.get(row['path'],(ROOT/row['path']).read_text()))
        row['sha256' if 'sha256' in row else 'after']=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

def runtime_files():
    return {n:(ROOT/'runtime/wasm32'/n).read_text() for n in ('collector.c','collector-owner.mjs')}
