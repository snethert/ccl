"""Compile unchanged integrated compiler in a disposable pristine U1 copy."""
import importlib.util,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def run(e,out,command):
 driver=out/'driver';shutil.copytree(HERE.parent/'constants',driver,ignore=shutil.ignore_patterns('__pycache__'))
 shutil.copy(HERE/'compile.lisp',driver/'compile.lisp')
 p=driver/'compile.py';s=p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",f"ROOT=Path({str(ROOT)!r});REG=ROOT/'tests/wasm/stage1/registration'");p.write_text(s)
 # Import the driver from the new directory, including its historical generator
 # dependency; the supplied backend overrides that generator completely.
 sys.path.insert(0,str(driver))
 spec=importlib.util.spec_from_file_location('symbol_compile',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.run(e,out/'compiled',(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text())
 import encode
 encode.Encoder.__init__.__defaults__=(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
 from pool import compile_pool
 graph=json.loads((out/'compiled/pools.json').read_text());pool=compile_pool(graph);material=pool.at(2097152)
 (out/'compiled/materialized.json').write_text(json.dumps(dict(image=material.image.hex(),roots=material.roots),sort_keys=True,indent=2)+'\n')
 command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',HERE/'adapter.wat','-o',out/'adapter.wasm'],out/'adapter-build.log')
