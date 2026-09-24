"""String constructor proposal over the accepted R12 integrated sources."""
from pathlib import Path
import hashlib
import subprocess
import shutil
import build as builder
import common as c
HERE=Path(__file__).resolve().parent
BACKEND='compiler/WASM32/wasm32-backend.lisp'

def generate():
    text=(c.ROOT/BACKEND).read_text()
    anchor="          ((eq name '-) (bootstrap-subtract forms))"
    assert text.count(anchor)==1
    return text.replace(anchor,anchor+'\n'+(HERE/'thread-local.lisp').read_text())

def sources():
    text=(c.ROOT/'level-1/l1-streams.lisp').read_text()
    old="       (let* ((loc (%tcr-binding-location (%current-tcr) '%string-output-stream-ioblocks%)))"
    assert text.count(old)==1
    return {'level-1/l1-streams.lisp':text.replace(old,
        "       #+wasm32-target (%wasm-thread-local-value '%string-output-stream-ioblocks%)\n       #-wasm32-target\n"+old)}

def install():
    if getattr(builder,'ready_proposal',False):return
    environment,prepare=builder.environment,builder.prepare
    # The previous proposal stack is integrated. Read its complete source list,
    # then use the current product files exactly once, without replaying patches.
    record=c.read(c.ROOT/'doc/WASM/stage1/acceptance-ready-runtime.json')
    native=c.STORE/'2026-09-24-stage1-ready-runtime-acceptance'
    identity=c.read(native/'proposal-identity.json')
    def source_files():
        result={name:(c.ROOT/name).read_text() for name in identity}
        result[BACKEND]=generate();result.update(sources());return result
    def identity_key():
        return dict(**environment(),ready_compiler=dict(
            sources={name:hashlib.sha256(text.encode()).hexdigest() for name,text in source_files().items()},
            collector=c.sha(c.ROOT/'runtime/wasm32/collector.c'),
            clang=c.sha(Path('/usr/local/opt/llvm/bin/clang')),
            drivers={name:c.sha(HERE/name) for name in
                ('compiler.py','thread-local.lisp','numeric-files.lisp','graph.lisp','clos-methods.lisp','condition-methods.lisp')}))
    def proposed(parent,stage):
        prepare(parent,stage)
        for src,dst in [('numeric-files.lisp','numeric-files.lisp'),('graph.lisp','graph.lisp'),
                        ('clos-methods.lisp','ready-clos-methods.lisp'),('condition-methods.lisp','condition-methods.lisp')]:
            shutil.copyfile(HERE/src,stage/'driver'/dst)
        # Preserve method qualifiers when binding the real native method object.
        for path in (stage/'driver').glob('*.lisp'):
            text=path.read_text()
            if '(destructuring-bind (name classes entry) spec' in text:
                text=text.replace('(destructuring-bind (name classes entry) spec','(destructuring-bind (name classes entry &optional qualifiers) spec')
                text=text.replace("(find-method gf nil (mapcar #'find-class classes))","(find-method gf qualifiers (mapcar #'find-class classes))")
                path.write_text(text)
        controls=stage/'driver/controls.lisp'
        old="(:bit-vector-kind (defun refused (x) (declare (type (simple-array bit (*)) x)) (aref x 0)) :bootstrap-array-kind)"
        text=controls.read_text();assert text.count(old)==1
        controls.write_text(text.replace(old,old.replace(':bootstrap-array-kind)', ':admitted)')))
        c.save(stage/'driver-manifest.json',c.inventory(stage/'driver'))
        root=stage/'compiled/proposal';manifest=dict(source_revision='c994217adc56b3f8a564526cee4695893ac84d86',added=[],modified=[])
        shutil.rmtree(root/'files');(root/'files').mkdir()
        for name,text in source_files().items():
            path=root/'files'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            original=subprocess.run(['git','show',manifest['source_revision']+':'+name],cwd=c.ROOT,capture_output=True)
            if original.returncode:
                manifest['added'].append(dict(path=name,sha256=c.sha(path)))
            else:
                manifest['modified'].append(dict(path=name,before=hashlib.sha256(original.stdout).hexdigest(),after=c.sha(path)))
        c.save(root/'unit.json',manifest)
        shutil.copyfile(c.ROOT/'runtime/wasm32/collector.c',stage/'runtime/collector.c')
        clang=Path('/usr/local/opt/llvm/bin/clang')
        c.command([clang,'--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
          '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
          '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
          stage/'runtime/collector.c','-o',stage/'ready-collector.wasm'],stage/'collector-build.log')
        c.save(stage/'ready-runtime.json',{'collector.wasm':c.sha(stage/'ready-collector.wasm'),'source':c.sha(stage/'runtime/collector.c')})
    builder.environment,builder.prepare=identity_key,proposed
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
