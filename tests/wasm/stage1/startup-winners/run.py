import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from derive import derive,ROOT
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'startup-joined'));from compile import compile_source
CLANG='/usr/local/opt/llvm/bin/clang';NODE='/usr/local/bin/node';WABT='/usr/local/bin/wat2wasm'
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=__stack_pointer']
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),check=True,stdout=f,stderr=subprocess.STDOUT,timeout=300)
def build(p,out):command([CLANG,*FLAGS,*['-Wl,--export='+x for x in ['ht_size','ht_init','ht_run']],p,'-o',out],out.with_suffix('.log'))
def run(e,out):
 out.mkdir(parents=True,exist_ok=False);(out/'hash.c').write_text(derive());build(out/'hash.c',out/'hash.wasm')
 c=compile_source(e,out/'compile',(HERE/'compile.lisp').read_text(),None);shutil.copytree(c,out/'compiled',ignore=shutil.ignore_patterns('source','proposal','compile-input'))
 command([WABT,'--enable-threads','--enable-exceptions',ROOT/'runtime/wasm32/hash-adapter.wat','-o',out/'adapter.wasm'],out/'adapter.log')
 for n in ['check.mjs']:shutil.copy(HERE/n,out/n)
 # Rebuild the integrated collector; original hash operation corpus is replayed
 # against the new service with its retained binary and native oracle.
 command([CLANG,*FLAGS,'-Wl,--export=collect',ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],out/'collector.log')
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 # Reuse the accepted hash-table primitive and generated operation oracles.
 parent=e/'2026-09-20-stage1-hash-tables-r1'
 for row in read(parent/'packet.json')['files']:assert sha(parent/row['path'])==row['sha256']
 old=parent/'execution';reg=out/'inherited';reg.mkdir()
 for n in ['trace.json','native.json','generated.mjs','adapter.wasm']:shutil.copy(old/n,reg/n)
 shutil.copy(ROOT/'tests/wasm/stage1/hash-tables/check.mjs',reg/'check.mjs')
 shutil.copytree(old/'compiled',reg/'compiled')
 for n in ['hash.wasm','collector.wasm']:shutil.copy(out/n,reg/n)
 for mode in ['', 'generated']:
  dest=reg/('generated.json' if mode else 'execution.json')
  command([NODE,reg/'check.mjs',reg,dest,*([mode] if mode else [])],dest.with_suffix('.log'))
  assert read(dest)==read(old/dest.name),'inherited '+mode
 faults=[
  ('last-bucket','ht_init(b,end,n);v=table;','U saved=L(b+60+8*(n-1));ht_init(b,end,n);S(b+60+8*(n-1),saved);v=table;','bucket key cleared'),
  ('padding','ht_init(b,end,n);v=table;','ht_init(b,end,n);S(end-4,4);v=table;','padding zero'),
  ('return-identity','ht_init(b,end,n);v=table;','ht_init(b,end,n);v=NIL;','native return identity'),
  ('stale-cache','ht_init(b,end,n);v=table;','ht_init(b,end,n);S(b+44,77838);v=table;','cache key cleared'),
  ('live-bucket','ht_init(b,end,n);v=table;','ht_init(b,end,n);S(b+60,77838);v=table;','bucket key cleared'),
  ('live-value','ht_init(b,end,n);v=table;','ht_init(b,end,n);S(b+64,77838);v=table;','bucket value cleared'),
  ('dead-count','ht_init(b,end,n);v=table;','ht_init(b,end,n);S(b+32,4);v=table;','tombstones cleared'),
  ('moved-flag','ht_init(b,end,n);v=table;','ht_init(b,end,n);S(b+8,TRACK|MOVED);v=table;','moved flag cleared'),
  ('early-publication',' if((scratch&7)', ' if(op==5)S(result,table);\n if((scratch&7)','refusal preserves'),
 ]
 controls=[]
 for name,oldtext,newtext,diagnostic in faults:
  m=out/'faults'/name;m.mkdir(parents=True);source=(out/'hash.c').read_text();assert source.count(oldtext)==1
  (m/'hash.c').write_text(source.replace(oldtext,newtext));build(m/'hash.c',m/'hash.wasm')
  for n in ['check.mjs','adapter.wasm','collector.wasm']:shutil.copy(out/n,m/n)
  shutil.copytree(out/'compiled',m/'compiled')
  try:command([NODE,m/'check.mjs',m,m/'execution.json'],m/'execution.log')
  except subprocess.CalledProcessError:
   assert diagnostic in (m/'execution.log').read_text(),name;controls.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
  else:raise AssertionError('escaped '+name)
 save(out/'controls.json',controls)
 summary=read(out/'execution.json')['summary'];summary.update(mutants=len(controls),inherited_primitive_and_generated_identical=True,modules=len(read(out/'compiled/modules.json')))
 save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
