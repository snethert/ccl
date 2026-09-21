import importlib.util,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def compile_source(e,out,source,selection):
 out.mkdir();driver=out/'driver';shutil.copytree(ROOT/'tests/wasm/stage1/constants',driver,ignore=shutil.ignore_patterns('__pycache__'))
 (driver/'compile.lisp').write_text(source)
 if selection:(driver/'selection.lisp').write_text(selection)
 p=driver/'compile.py';s=p.read_text();old="ROOT=HERE.parents[3];REG=HERE.parent/'registration'";assert old in s;p.write_text(s.replace(old,f"ROOT=Path({str(ROOT)!r});REG=ROOT/'tests/wasm/stage1/registration'"))
 sys.path.insert(0,str(driver));spec=importlib.util.spec_from_file_location('joined_compile_driver',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.run(e,out/'compiled',(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text())
 import encode
 encode.Encoder.__init__.__defaults__=(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
 from pool import compile_pool
 mat=compile_pool(json.loads((out/'compiled/pools.json').read_text())).at(2097152)
 (out/'compiled/materialized.json').write_text(json.dumps(dict(image=mat.image.hex(),roots=mat.roots),indent=2,sort_keys=True)+'\n')
 return out/'compiled'
