import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from derive import derive
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CONFIG='2026-09-20-stage1-startup-config-r2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,why=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=300)
 if why:assert r.returncode and why in log.read_text(),log
 else:assert r.returncode==0,log

def run(e,out):
 out.mkdir(parents=True)
 native=read(e/CONFIG/'native-reuse.json');assert native['compiler_sha256']==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp');save(out/'native-reuse.json',native)
 (out/'owner.mjs').write_text(derive())
 for n in ['statistics.mjs','service.mjs','check.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['sha256.mjs','bytes.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 sys.path.insert(0,str(HERE.parent/'startup-joined'));from compile import compile_source
 c=compile_source(e,out/'compile',(HERE/'compile.lisp').read_text(),None)
 shutil.copytree(c,out/'compiled',ignore=shutil.ignore_patterns('source','proposal','compile-input','compiler.dx64fsl'))
 clang='/usr/local/opt/llvm/bin/clang';node='/usr/local/bin/node';wabt='/usr/local/bin/wat2wasm'
 flags=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer']
 command([clang,*flags,ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],out/'collector-build.log')
 command([wabt,'--enable-threads','--enable-exceptions',ROOT/'runtime/wasm32/hash-adapter.wat','-o',out/'adapter.wasm'],out/'adapter-build.log')
 command([node,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 # Original owner checks import its local owner. Copy the unchanged harness to
 # this proposal directory so all 40 standalone checks exercise the overlay.
 shutil.copy(ROOT/'tests/wasm/stage1/collector-owner/check.mjs',out/'owner-check.mjs')
 command([node,out/'owner-check.mjs',out/'collector.wasm',out/'owner-inherited.json'],out/'owner-inherited.log')
 from controls import controls
 controls(out,command,save)
 from classify import classify,validate
 manifest=classify();assert read(HERE/'classification.json')==manifest;save(out/'classification.json',manifest);save(out/'classification-check.json',validate(manifest))
 save(out/'tools.json',{str(Path(p)):sha(Path(p)) for p in [clang,node,wabt]})
 save(out/'summary.json',dict(read(out/'execution.json'),owner_checks=read(out/'owner-inherited.json')['checks'],compiler_unchanged=True,slot_credit=False,controls=len(read(out/'controls.json'))))
 print({k:v for k,v in read(out/'summary.json').items() if k!='rows'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
