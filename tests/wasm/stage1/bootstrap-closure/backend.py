"""Next execution proposal over the accepted audit-153 source."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PACKET=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-math-r2/execution/compiled/proposal'
BACKEND='compiler/WASM32/wasm32-backend.lisp'
ARCH='compiler/WASM32/wasm32-arch.lisp'

def generate():
    text=(ROOT/BACKEND).read_text()
    old="(every (lambda (form) (ccl::acode-form-typep form '(unsigned-byte 32) t)) forms)"
    new="""(every (lambda (form)
                      (or (ccl::acode-form-typep form '(unsigned-byte 32) t)
                          (and (ccl::acode-p form)
                               (member (ccl::acode-operator-name (ccl::acode-operator form))
                                       '(ccl::fixnum ccl::immediate))
                               (typep (car (ccl::acode-operands form)) '(unsigned-byte 32)))))
                    forms)"""
    assert text.count(old)==1
    return text.replace(old,new)

def source_files(src):
    manifest=json.loads((PACKET/'unit.json').read_text())
    return {r['path']:(ROOT/r['path']).read_text() for r in manifest['added']+manifest['modified'] if r['path'].startswith(('level-0/','level-1/'))}

def proposal(src,out):
    shutil.copytree(PACKET,out)
    manifest=json.loads((out/'unit.json').read_text())
    changed={BACKEND:generate(),**source_files(src)}
    for row in manifest['added']+manifest['modified']:
        p=out/'files'/row['path'];p.write_text(changed.get(row['path'],(ROOT/row['path']).read_text()))
        row['sha256' if 'sha256' in row else 'after']=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

def runtime_files():
    return {n:(ROOT/'runtime/wasm32'/n).read_text() for n in ('collector.c','collector-owner.mjs')}
