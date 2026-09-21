import argparse,hashlib,importlib.util,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'startup-joined'));from compile import compile_source
CLANG='/usr/local/opt/llvm/bin/clang';NODE='/usr/local/bin/node';WABT='/usr/local/bin/wat2wasm'
PARENT='2026-09-20-stage1-startup-winners-review-r1'
CONFIG='2026-09-20-stage1-startup-config-r2'
SOURCES=('db.c','compile.lisp','check.mjs','run.py','packet.py','README.md','scope.json')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,why=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=300)
 if why:assert r.returncode and why in log.read_text(),log
 else:assert r.returncode==0,log

def pins(e):
 tools=read(e/'2026-09-20-stage1-hash-tables-r1/toolchain.json')['tools']
 for t in [CLANG,NODE,WABT]:assert sha(Path(t)) in [r['sha256'] for r in tools],t
 native=read(e/CONFIG/'execution/config/compiled/command.json')
 for name,key in [('2026-09-12-native-census-r7/baseline/build/dx86cl64','kernel_sha256'),('2026-09-16-stage1-1a-r2/native/baseline.image','image_sha256')]:assert sha(e/name)==native[key],name
 p=read(e/PARENT/'source-pins.json')
 for n,h in p.items():assert sha(ROOT/n)==h,n
 for f in [*(HERE/n for n in SOURCES),*(ROOT/n for n in ['lib/db-io.lisp','lib/foreign-types.lisp','compiler/dll-node.lisp','compiler/X86/X8632/x8632-arch.lisp','runtime/wasm32/hash-adapter.wat'])]:p[str(f.relative_to(ROOT))]=sha(f)
 return dict(sorted(p.items()))
def controls(out):
 code=(out/'db.c').read_text();rows=[]
 for name,a,b,diagnostic in [
  ('last-slot','slot<12','slot<11','DB slots and preserved metadata'),
  ('skip-last-dir','for(U slot=5;', 'if(L(p+12)==head)break;for(U slot=5;', 'DB slots and preserved metadata'),
  ('omit-publication','S(result+12,0);','', 'DB publication'),
  ('refusal-write','if(op!=5)return 5;','if(op!=5){S(base+16,NIL);return 5;}','DB refusal preserves image'),
 ]:
  assert code.count(a)==1,name
  d=out/'faults'/name;d.mkdir(parents=True);(d/'db.c').write_text(code.replace(a,b));shutil.copy(out/'adapter.wasm',d/'adapter.wasm');shutil.copytree(out/'compiled',d/'compiled')
  command([CLANG,*FLAGS,'-Wl,--export=db_run',d/'db.c','-o',d/'db.wasm'],d/'build.log')
  command([NODE,out/'check.mjs',d,d/'execution.json'],d/'rejected.log',diagnostic)
  rows.append(dict(name=name,diagnostic=diagnostic,status='REJECTED',binary=sha(d/'db.wasm')))
 save(out/'controls.json',rows)
def finish(e,out,source):
 controls(out);assert pins(e)==source
 save(out/'summary.json',dict(read(out/'execution.json')['summary'],native_answers=len(read(out/'compiled/native.json')),faults=len(read(out/'controls.json')),source_pins=len(source),compiler_unchanged=True))
 print(read(out/'summary.json'))

def run(e,out):
 source=pins(e);out.mkdir(parents=True,exist_ok=False)
 reuse=read(e/CONFIG/'native-reuse.json');assert reuse['compiler_sha256']==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp');save(out/'native-reuse.json',reuse)
 arch=(ROOT/'compiler/X86/X8632/x8632-arch.lisp').read_text()
 assert '(defconstant ntagbits 3)' in arch and '(defconstant fulltag-nodeheader 2)' in arch and '(define-node-subtag struct 15)' in arch
 save(out/'layout.json',dict(subtag=(15<<3)|2,header_words=4,node_words=12,slots=list(range(5,12)),source='native uvsize/uvref plus pinned D1 subtag',snapshot_id=13017,registry_ordinal=27))
 c=compile_source(e,out/'compile',(HERE/'compile.lisp').read_text(),None);shutil.copytree(c,out/'compiled',ignore=shutil.ignore_patterns('source','proposal','compile-input'))
 shutil.copy(HERE/'db.c',out/'db.c');shutil.copy(HERE/'check.mjs',out/'check.mjs')
 command([CLANG,*FLAGS,'-Wl,--export=db_run',out/'db.c','-o',out/'db.wasm'],out/'build.log')
 command([WABT,'--enable-threads','--enable-exceptions',ROOT/'runtime/wasm32/hash-adapter.wat','-o',out/'adapter.wasm'],out/'adapter.log')
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 finish(e,out,source)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
