#!/usr/bin/env python3
"""Compile the pool proposal only inside a disposable pristine U1 archive."""
import json,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
from compiler import generate
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];REG=HERE.parent/'registration'
sys.path.insert(0,str(REG))
from unit import Unit,proposal,sha,save

def run(evidence,out,backend_text=None):
    out.mkdir(parents=True,exist_ok=False)
    (out/'source').mkdir()
    for name in ('compiler.py','compiler-extension.lisp','compile.py','compile.lisp','export.lisp','function-layout.json','execute_compiled.py','execute_compiled.mjs','transport.mjs','loader.mjs','binary.mjs','stub.wat'):
        shutil.copy(HERE/name,out/'source'/name)
    with tempfile.TemporaryDirectory(prefix='ccl-pool-compile-') as temp:
        work=Path(temp);src=work/'ccl';src.mkdir();save(work/'stage1-disposable.json',{'source':str(src)})
        inputs=evidence/'macos-u1-inputs';pins=json.loads((inputs/'pins.json').read_text())
        for name in ('source.tar','bootstrap.tar.gz'):
            assert sha(inputs/name)==pins['inputs'][name]
            with tarfile.open(inputs/name) as t:t.extractall(src,filter='data')
        kernel=evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64'
        image=evidence/'2026-09-16-stage1-1a-r2/native/baseline.image'
        shutil.copy(kernel,src/'dx86cl64');(src/'dx86cl64').chmod(0o755);shutil.copy(image,src/'dx86cl64.image')
        m=proposal(src,out/'proposal');backend=out/'proposal/files/compiler/WASM32/wasm32-backend.lisp';backend.write_text(generate() if backend_text is None else backend_text)
        next(r for r in m['added'] if r['path']=='compiler/WASM32/wasm32-backend.lisp')['sha256']=sha(backend);save(out/'proposal/unit.json',m)
        with Unit(src,out/'proposal'):
            cmd=[str(src/'dx86cl64'),'--no-init','--batch','--eval','(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp"))','--load',str(REG/'load.lisp'),'--load',str(HERE/'compile.lisp')]
            env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(src),'POOL_OUTPUT':str(out)+'/'}
            save(out/'command.json',{'argv':cmd,'environment':env,'inputs':pins,'kernel_sha256':sha(kernel),'image_sha256':sha(image)})
            with (out/'compile.log').open('w') as log:r=subprocess.run(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            if r.returncode or 'POOL-COMPILE-PASS' not in (out/'compile.log').read_text():raise RuntimeError(str(out/'compile.log'))
            shutil.copy(src/'bin/wasm32-backend.dx64fsl',out/'compiler.dx64fsl')
        assert all(sha(src/r['path'])==r['before'] for r in m['modified'])
    for p in out.glob('*.wat'):
      with (out/(p.stem+'.wabt.log')).open('w') as log:
        subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(p),'-o',str(p.with_suffix('.wasm'))],check=True,stdout=log,stderr=subprocess.STDOUT)
    print('PASS: generated',len(list(out.glob('*.wasm'))),'modules')

if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
