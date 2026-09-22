from pathlib import Path
import json,subprocess,sys,shutil
h=Path(__file__).resolve().parent;r=h.parents[3];p=h.parent/'bootstrap-values';o=Path(sys.argv[1]).resolve();d=o/'driver'
sys.path.insert(0,str(d));import encode
encode.Encoder.__init__.__defaults__=(r/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
from pool import compile_pool
owners=json.loads((o/'compiled/symbols.json').read_text());pool=compile_pool(json.loads((o/'compiled/pools.json').read_text()),{x['id']:600006+32*i for i,x in enumerate(owners)})
mat=pool.at(2097152);(o/'compiled/materialized.json').write_text(json.dumps(dict(image=mat.image.hex(),roots=mat.roots)))
(o/'compiled/moving-pools.json').write_text(json.dumps({str(b):dict(image=pool.at(b).image.hex(),roots=pool.at(b).roots) for b in [262144,2147483648]}))
sys.path.insert(0,str(h));import backend
runtime=o/'runtime';runtime.mkdir(exist_ok=True)
for f in (r/'runtime/wasm32').glob('*.mjs'):shutil.copy(f,runtime/f.name)
for name,text in backend.runtime_files().items():(runtime/name).write_text(text)
for name in ('install.mjs','check.mjs','gf-check.mjs','installer-check.mjs','metadata-check.mjs'):shutil.copy(h/name,o/name)
sys.path.insert(0,str(h.parent/"bootstrap-core"));import probe;probe.build(o/'compiled')
clang='/usr/local/opt/llvm/bin/clang';baseflags=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,-z,stack-size=65536']
for name,extra in [('collector',['-matomics','-mbulk-memory','-Wl,--shared-memory','-Wl,--global-base=1048576','-Wl,--export=collect','-Wl,--export=__stack_pointer']),('integer',['-Wl,--global-base=65536','-Wl,--export=integer_calculate','-Wl,--export=integer_workspace_bytes'])]:
 subprocess.run([clang,*baseflags,*extra,r/f'runtime/wasm32/{name}.c','-o',o/f'{name}.wasm'],check=True)
import importlib.util
spec=importlib.util.spec_from_file_location('math_build',r/'runtime/wasm32/build-float.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build);build.build(o,runtime)
subprocess.run(['/usr/local/bin/wat2wasm',r/'runtime/wasm32/float-detector.wat','-o',o/'detector.wasm'],check=True)
shutil.copy(r.parent/'ccl-evidence/2026-09-21-stage1-population-pushnew-r1/execution/eql.wasm',o/'eql.wasm')
subprocess.run(['/usr/local/bin/wat2wasm','--enable-tail-call',r/'runtime/wasm32/stub.wat','-o',o/'stub.wasm'],check=True)
with (o/'execution.log').open('w') as log:subprocess.run(['/usr/local/bin/node',o/'check.mjs',o,o/'execution.json'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)

shutil.copy(h/'istruct-check.mjs',o/'istruct-check.mjs')
subprocess.run(['/usr/local/bin/node',o/'istruct-check.mjs',o/'collector.wasm',o/'istruct-checks.json'],check=True)
