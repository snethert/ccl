"""READY numerical closure over the accepted R9 compiler; isolated proposal."""
from pathlib import Path
import hashlib
import build as builder
import common as c

HERE=Path(__file__).resolve().parent
BACKEND='compiler/WASM32/wasm32-backend.lisp'

def generate():
    text=(c.ROOT/BACKEND).read_text()
    assert c.sha(c.ROOT/BACKEND)=='0965018e116b3b7e8e9765cda2cc4399e07e4197e7f9bad3e14372d3287a78d6'
    anchor='(defun bootstrap-operator (ir)'
    assert text.count(anchor)==1
    text=text.replace(anchor,(HERE/'complex-floats.lisp').read_text()+'\n'+anchor)
    anchor='    (case op\n      ((ccl::%setf-double-float ccl::%setf-short-float)'
    assert text.count(anchor)==1
    text=text.replace(anchor,'    (case op\n      ((ccl::%complex-single-float-realpart ccl::%complex-single-float-imagpart\n        ccl::%complex-double-float-realpart ccl::%complex-double-float-imagpart)\n       (bootstrap-complex-part op args))\n      ((ccl::%make-complex-single-float ccl::%make-complex-double-float)\n       (bootstrap-complex-float op args))\n      ((ccl::%setf-double-float ccl::%setf-short-float)')
    return text

def install():
    if getattr(builder,'ready_proposal',False):return
    environment,prepare=builder.environment,builder.prepare
    def identity():
        return dict(**environment(),ready_compiler=dict(
            collector=c.sha(c.ROOT/'runtime/wasm32/collector.c'),
            clang=c.sha(Path('/usr/local/opt/llvm/bin/clang')),lap=c.sha(c.ROOT/'level-0/WASM32/w32-lap.lisp'),
            base=c.sha(c.ROOT/BACKEND),proposal=hashlib.sha256(generate().encode()).hexdigest(),
            derivation=c.sha(Path(__file__)),
            complex_floats=c.sha(HERE/'complex-floats.lisp'),
            class_driver=c.sha(HERE/'numeric-files.lisp'),
            clos_methods=c.sha(HERE/'clos-methods.lisp'),
            condition_methods=c.sha(HERE/'condition-methods.lisp'),
            graph=c.sha(HERE/'graph.lisp')))
    def proposed(parent,stage):
        prepare(parent,stage)
        (stage/'driver/numeric-files.lisp').write_bytes((HERE/'numeric-files.lisp').read_bytes())
        (stage/'driver/graph.lisp').write_bytes((HERE/'graph.lisp').read_bytes())
        (stage/'driver/ready-clos-methods.lisp').write_bytes((HERE/'clos-methods.lisp').read_bytes())
        (stage/'driver/condition-methods.lisp').write_bytes((HERE/'condition-methods.lisp').read_bytes())
        controls=stage/'driver/controls.lisp'
        old="(:bit-vector-kind (defun refused (x) (declare (type (simple-array bit (*)) x)) (aref x 0)) :bootstrap-array-kind)"
        text=controls.read_text();assert text.count(old)==1
        controls.write_text(text.replace(old,old.replace(':bootstrap-array-kind)', ':admitted)')))
        c.save(stage/'driver-manifest.json' ,c.inventory(stage/'driver'))
        path=stage/'compiled/proposal/files'/BACKEND
        path.write_text(generate())
        manifest=stage/'compiled/proposal/unit.json'
        record=c.read(manifest)
        row=next(r for r in record['added'] if r['path']==BACKEND)
        row['sha256']=c.sha(path)
        lap='level-0/WASM32/w32-lap.lisp'
        source=(c.ROOT/lap).read_text()
        source+='''
;;; Single-float counterpart of the native destructive absolute value.
(defun %%short-float-abs! (n result)
  (declare (single-float n result))
  (%wasm-set-float-word result 0
                        (logand #x7fffffff
                                (the (unsigned-byte 32) (%wasm-float-word n 0))))
  result)
'''
        (stage/'compiled/proposal/files'/lap).write_text(source)
        next(r for r in record['added'] if r['path']==lap)['sha256']=c.sha(stage/'compiled/proposal/files'/lap)
        c.save(manifest,record)
        collector=(c.ROOT/'runtime/wasm32/collector.c').read_text()
        anchor=' case 23:return n==3?12:0xffffffffu;'
        assert collector.count(anchor)==1
        collector=collector.replace(anchor,anchor+'\n case 71:return n==3?12:0xffffffffu;\n case 79:return n==5?20:0xffffffffu;')
        (stage/'runtime/collector.c').write_text(collector)
        clang=Path('/usr/local/opt/llvm/bin/clang')
        c.command([clang,'--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
          '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
          '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
          stage/'runtime/collector.c','-o',stage/'ready-collector.wasm'],stage/'collector-build.log')
        c.save(stage/'ready-runtime.json',{'collector.wasm':c.sha(stage/'ready-collector.wasm'),'source':c.sha(stage/'runtime/collector.c')})
    builder.environment,builder.prepare=identity,proposed
    builder.ready_proposal=True
    import execute
    execute.prepare=execution_prepare


def execution_prepare(out):
    from prepare import prepare
    import shutil
    result=prepare(out)
    record=c.read(out/'ready-runtime.json')
    assert c.sha(out/'ready-collector.wasm')==record['collector.wasm']
    assert c.sha(out/'runtime/collector.c')==record['source']
    shutil.copyfile(out/'ready-collector.wasm',out/'collector.wasm')
    environment=c.read(out/'execution-environment.json')
    environment['files']['collector.wasm']=record['collector.wasm']
    environment['tooling']['ready/compiler.py']=c.sha(Path(__file__))
    c.save(out/'execution-environment.json',environment)
    return result
