"""Full compiler regression over the integrated source identity plus this proposal."""
from pathlib import Path
import importlib.util
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import build
import storage
import proposal


def sources():
    native=c.STORE/'2026-09-24-namespace-consumers-r1/native/qualification.json'
    identity=c.read(native)['source_identity']
    c.verify_files(c.ROOT,identity)
    bodies={name:(c.ROOT/name).read_text() for name in identity}
    bodies.update(proposal.sources())
    return bodies


def corpus(out):
    out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('cross_load_compiler',HERE.parent/'ready/compiler.py')
    compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
    bodies=sources();key='compiler/WASM32/wasm32-backend.lisp'
    compiler.generate=lambda:bodies[key]
    compiler.sources=lambda:{name:body for name,body in bodies.items() if name!=key}
    compiler.install()
    result=build.build(out/'base',c.DEFAULT_CACHE,cold=True)
    c.save(out/'cold-compiler.json',result)
    import execute
    result=execute.execute(out/'base',4,'full')
    c.save(out/'regression.json',result)
    print('CROSS-LOAD-CORPUS',result,flush=True)


if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):corpus(Path(sys.argv[1]).resolve())
