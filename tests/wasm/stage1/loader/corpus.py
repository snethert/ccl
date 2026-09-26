"""Full compiler corpus against the exact loader proposal, without Git."""
from pathlib import Path
import importlib.util
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import build as builder
import storage
import proposal

def run(out, source_provider=None, prepare_execution=None, runtime_identity=None, native_prelude=None):
    out.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('loader_compiler',HERE.parent/'ready/compiler.py')
    compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
    bodies=(source_provider or proposal.sources)();key='compiler/WASM32/wasm32-backend.lisp'
    compiler.generate=lambda:bodies[key]
    compiler.sources=lambda:{name:body for name,body in bodies.items() if name!=key}
    compiler.install()
    environment=builder.environment
    builder.environment=lambda:dict(environment(),loader_driver=c.sha(Path(__file__)), proposed_runtime=runtime_identity, native_prelude=native_prelude)
    command=c.command
    def preload(argv,*args,**kwargs):
        marker=c.ROOT/'tests/wasm/stage1/registration/load.lisp'
        if marker in argv:
            at=argv.index(marker)-1
            argv=argv[:at]+['--eval','(ccl::in-development-mode (load "ccl:xdump;faslenv.lisp") (load (compile-file "ccl:lib;nfcomp.lisp")))']+argv[at:]
        if native_prelude and any(str(x).endswith('/driver/native.lisp') for x in argv):
            at=argv.index('--load')
            argv=argv[:at]+['--eval',native_prelude]+argv[at:]
        return command(argv,*args,**kwargs)
    c.command=preload
    result=builder.build(out/'base',c.DEFAULT_CACHE,cold=True)
    c.save(out/'cold-compiler.json',result)
    import execute
    if prepare_execution is not None:
        execute.prepare=prepare_execution
    result=execute.execute(out/'base',4,'full')
    c.save(out/'regression.json',result)
    print('LOADER-CORPUS',result,flush=True)

if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):run(Path(sys.argv[1]).resolve())
