"""Isolated funcallable-instance layout over the hyperbolic proposal."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('gf_parent',HERE.parent/'bootstrap-hyperbolic/backend.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
BACKEND,ARCH,PACKET=parent.BACKEND,parent.ARCH,parent.PACKET

def generate():
    text=parent.generate()
    marker='(defun bootstrap-make-vector (forms)';assert text.count(marker)==1
    text=text.replace(marker,(HERE/'immediates.lisp').read_text()+'\n'+marker)
    old="    (cond ((member name '(ccl::%copy-double-float";assert text.count(old)==1
    text=text.replace(old,"""    (cond ((eq name 'ccl::%wasm-function-immediate)
           (b-multiple (make-b-raw-code :text (bootstrap-function-immediate forms nil))))
          ((eq name 'ccl::%wasm-set-function-immediate)
           (b-multiple (make-b-raw-code :text (bootstrap-function-immediate forms t))))
          ((eq name 'ccl::%wasm-make-funcallable-instance)
           (b-multiple (make-b-raw-code :text (bootstrap-make-funcallable forms))))
          ((member name '(ccl::%copy-double-float""")
    # Preserve default entry points byte for byte. The bootstrap profile admits
    # the second callable header and checks its vector at every callable check.
    a=text.index('(defun b-object-runtime ()');b=text.index('\n;;; Closure proposal:',a)
    body=text[a:b];assert body.count('~')==0
    body=body.replace('  "(func $span','  (b-wat "(func $span',1)
    old='    (if (i32.ne (i32.load (local.get $p)) (local.get $header))'
    assert body.count(old)==1
    body=body.replace(old,'~a'+old,1)
    assert body.endswith('\")\n')
    body=body[:-3]+'''"
    (if *bootstrap-front-end*
      "(if (i32.and (i32.eq (local.get $header) (i32.const 1578))
                    (i32.eq (i32.load (local.get $p)) (i32.const 1834)))
        (then (call $span (local.get $p) (i32.const 32))
              (drop (call $object_base (i32.load offset=28 (local.get $p)) (i32.const 32) (i32.const 2042)))
              (local.set $header (i32.const 1834))))\n"
      "")))
'''
    return text[:a]+body+text[b:]

def arch():
    text=(ROOT/ARCH).read_text()+'\n'+(HERE.parent/'bootstrap-arch/arch-macros.lisp').read_text()
    text=text.replace(';;; function object. Refuse reflection until its Lisp callers have a target\n;;; implementation; do not expose code ids or arity words as native literals.',
                      ';;; function object. Funcallable instances hold their seven Lisp immediates\n;;; in a separate traced vector; ordinary functions expose no native literals.')
    for name,args,call in [('nth-immediate','function index','%wasm-function-immediate'),('set-nth-immediate','function index value','%wasm-set-function-immediate')]:
        old=f'(arch::defarchmacro :wasm32 ccl::{name} ({args})\n  (declare (ignore {args}))\n  (refuse :function-immediate-layout))'
        new=f'(arch::defarchmacro :wasm32 ccl::{name} ({args})\n  `(ccl::{call} '+ ' '.join(','+x for x in args.split())+'))'
        assert text.count(old)==1;text=text.replace(old,new)
    return text

source_files=parent.source_files

def proposal(src,out):
    manifest=parent.proposal(src,out)
    for row in manifest['added']+manifest['modified']:
        name=row['path']
        if name in (BACKEND,ARCH):
            p=out/'files'/name;p.write_text(generate() if name==BACKEND else arch())
            row['sha256' if 'sha256' in row else 'after']=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

def runtime_files():
    spec=importlib.util.spec_from_file_location('gf_runtime',HERE/'runtime.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.derive()
