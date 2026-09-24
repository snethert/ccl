"""R6/R6a and native tests for the complete namespace compiler proposal."""
from pathlib import Path
import hashlib, importlib.util, sys, time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal as namespace_proposal
import storage

def sources():
    accepted=c.read(c.ROOT/'doc/WASM/stage1/integration-stream-constructors.json')['qualification']['source_identity']
    c.verify_files(c.ROOT,accepted)
    result={name:(c.ROOT/name).read_text() for name in accepted}
    result.update(namespace_proposal.sources())
    return result

def run(out):
    started=time.monotonic();out.mkdir(parents=True,exist_ok=True)
    bodies=sources();identity={name:hashlib.sha256(body.encode()).hexdigest() for name,body in bodies.items()}
    spec=importlib.util.spec_from_file_location('namespace_native_driver',HERE.parent/'bootstrap-generic-dispatch/native.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    driver=native.driver
    for name in list(namespace_proposal.sources())+['level-0/l0-aprims.lisp','level-0/l0-misc.lisp','level-1/l1-readloop.lisp']:
        if name.startswith(('level-0/l0-','level-1/l1-')) or name=='lib/foreign-types.lisp':
            fasl=name.replace('level-1/','l1-fasls/').replace('lib/','bin/').replace('.lisp','.dx64fsl')
            if (name,fasl) not in driver.SOURCE_PAIRS:driver.SOURCE_PAIRS.append((name,fasl))
    driver.EXPECTED=['bin/systems.dx64fsl','bin/compile-ccl.dx64fsl']+[p[1] for p in driver.SOURCE_PAIRS]
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
    assert identity=={name:hashlib.sha256(body.encode()).hexdigest() for name,body in sources().items()}
    c.save(out/'qualification.json',dict(status='PASS',source_identity=identity,
        native_run=c.sha(out/'results/run.json'),seconds=time.monotonic()-started))
    return status

if __name__=='__main__':
    sys.setrecursionlimit(20000)
    with storage.lease([Path(sys.argv[1])]):raise SystemExit(run(Path(sys.argv[1]).resolve()))
