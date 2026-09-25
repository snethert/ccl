"""R6/R6a for this branch's shared-source changes: nfcomp, faslenv, xfasload,
the wasm32 arch/backend/cross-loader, over the accepted identity set."""
from pathlib import Path
import hashlib, importlib.util, sys, time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import proposal
BRANCH=['lib/nfcomp.lisp','xdump/faslenv.lisp','xdump/xfasload.lisp','xdump/xwasm32-fasload.lisp',
        'compiler/WASM32/wasm32-arch.lisp','compiler/WASM32/wasm32-backend.lisp']
def accepted():
    names=list(c.read(c.ROOT/'doc/WASM/stage1/integration-stream-constructors.json')['qualification']['source_identity'])
    names+=[f['file'] for f in c.read(c.ROOT/'doc/WASM/stage1/integration-namespace-consumers.json')['files'] if f['file'].endswith('.lisp')]
    return sorted(set(names))
def sources():
    return proposal.sources()
def run(out):
    started=time.monotonic();out.mkdir(parents=True,exist_ok=True)
    bodies=sources();identity={name:hashlib.sha256(body.encode()).hexdigest() for name,body in bodies.items()}
    spec=importlib.util.spec_from_file_location('cross_load_native_driver',HERE.parent/'bootstrap-generic-dispatch/native.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    # Keep the established rebuild, native tests, snapshots and reversal. The
    # gate now decodes every changed artifact and names functional edit sites.
    qspec=importlib.util.spec_from_file_location('cross_loader_qualification',HERE/'qualify.py')
    qualify=importlib.util.module_from_spec(qspec);qspec.loader.exec_module(qualify)
    driver=native.driver
    text=(HERE.parent/'registration/run.py').read_text()
    old="if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))"
    assert text.count(old)==1
    text=text.replace(old,'qualify_all(source,out,inputs,baseline,registered)').replace("'identical':162","'identical':164-len(changed)")
    text=text.replace("HERE/'smoke.lisp'",repr(str(HERE/'smoke.lisp')))
    exec(compile(text,str(HERE.parent/'registration/run.py'),'exec'),driver.__dict__)
    driver.qualify_all=qualify.run
    def prepare(source,destination):
        destination.mkdir(parents=True)
        manifest=dict(source_revision='c994217adc56b3f8a564526cee4695893ac84d86',added=[],modified=[])
        for name,body in bodies.items():
            p=destination/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
            if (source/name).exists():manifest['modified'].append(dict(path=name,before=c.sha(source/name),after=identity[name]))
            else:manifest['added'].append(dict(path=name,sha256=identity[name]))
        c.save(destination/'unit.json',manifest);return manifest
    driver.proposal=prepare
    c.save(out/'proposal-identity.json',identity)
    status=driver.run(c.STORE/'macos-u1-inputs',c.KERNEL,out/'work',out/'results',c.STORE/'2026-09-16-stage1-1a-r2/native')
    assert status==0
    c.save(out/'qualification.json',dict(status='PASS',source_identity=identity,branch_sources=BRANCH,
        native_run=c.sha(out/'results/run.json'),seconds=time.monotonic()-started))
    return status
if __name__=='__main__':
    sys.setrecursionlimit(20000)
    with storage.lease([Path(sys.argv[1])]):raise SystemExit(run(Path(sys.argv[1]).resolve()))
