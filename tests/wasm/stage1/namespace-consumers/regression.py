"""Cold compiler build and unchanged original-definition execution corpus."""
from pathlib import Path
import importlib.util, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import build
import storage
import proposal

def compiler_setup():
    spec=importlib.util.spec_from_file_location('namespace_ready_compiler',HERE.parent/'ready/compiler.py')
    compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
    compiler.generate=lambda:proposal.sources()['compiler/WASM32/wasm32-backend.lisp']
    compiler.sources=lambda:{name:body for name,body in proposal.sources().items() if name!='compiler/WASM32/wasm32-backend.lisp'}
    compiler.install()
    return compiler

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    compiler_setup()
    result=build.build(out/'base',c.DEFAULT_CACHE,cold=True)
    c.save(out/'cold-compiler.json',result)
    import execute
    result=execute.execute(out/'base',4,'full')
    c.save(out/'regression.json',result)
    print(result,flush=True)
    return c.read(out/'cold-compiler.json')['key']

if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):run(Path(sys.argv[1]).resolve())
