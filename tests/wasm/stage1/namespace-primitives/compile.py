from pathlib import Path
import os
import shutil
import tarfile
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'bootstrap-validation'))
import common as c
def run(out):
    sources = ['compiler/WASM32/wasm32-backend.lisp', 'compiler/WASM32/wasm32-arch.lisp',
               'lib/systems.lisp','lib/compile-ccl.lisp','xdump/xwasm32-fasload.lisp']
    out.mkdir(parents=True, exist_ok=True)
    # Exporters create new files: never mix a failed compile with its successor.
    for path in out.glob('*.json'):path.unlink()
    env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(c.ROOT)+'/',
               FILES_OUTPUT=str(out)+'/', FILES_SOURCE=str(HERE)+'/')
    kernel=out/'dx86cl64'
    shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
    # Build only the integrated compiler and these two files (about two seconds).
    # No corpus projection or saved session is required to reproduce it.
    with tempfile.TemporaryDirectory(prefix='u1-',dir=out.parent) as temp:
        source=Path(temp)
        inputs=c.STORE/'macos-u1-inputs'
        for name in ('source.tar','bootstrap.tar.gz'):
            assert c.sha(inputs/name)==c.read(inputs/'pins.json')['inputs'][name]
            with tarfile.open(inputs/name) as archive:archive.extractall(source,filter='data')
        for name in sources:
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,path)
        env['CCL_DEFAULT_DIRECTORY']=str(source)+'/'
        argv=[kernel,'-I',c.IMAGE,'--no-init','--batch','--eval',
              '(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp"))',
              '--load',HERE.parent/'registration/load.lisp',
              '--load',HERE.parent/'constants/export.lisp',
              '--load',HERE.parent/'bootstrap-values/extra.lisp',
              '--load',HERE.parent/'bootstrap-validation/driver/whole-file.lisp',
              '--load',HERE/'compile.lisp']
        seconds=c.command(argv,out/'compile.log',env,cwd=source,timeout=180)
    assert 'NAMESPACE-COMPILE-PASS' in (out/'compile.log').read_text()
    with ThreadPoolExecutor(max_workers=4) as pool:
        assembled = list(pool.map(lambda p:c.assemble(p, c.DEFAULT_CACHE), sorted(out.glob('*.wat'))))
    sys.path.insert(0, str(HERE.parent/'constants'))
    import pool, encode
    encode.Encoder.__init__.__defaults__ = (c.ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
    symbols = {row['id']: 786438 + 32*i for i,row in enumerate(c.read(out/'symbols.json'))}
    compiled = pool.compile_pool(c.read(out/'pools.json'), symbols=symbols)
    material = compiled.at(2097152)
    roots, image = material.roots, material.image
    (out/'pool.bin').write_bytes(image)
    c.save(out/'pool-roots.json', roots)
    c.save(out/'compile-completion.json', dict(status='PASS', session=None,
        compiler_image=c.sha(c.IMAGE), sources={n:c.sha(c.ROOT/n) for n in sources},
        seconds=seconds, modules=len(assembled), assembly=assembled))

if __name__ == '__main__':run(Path(sys.argv[1]).resolve())
