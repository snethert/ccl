import argparse,hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
from derive import HERE,ROOT,adapter,generated
E=ROOT.parent/'ccl-evidence';CLANG=Path('/usr/local/opt/llvm/bin/clang');NODE=Path('/usr/local/bin/node');WABT=Path('/usr/local/bin/wat2wasm')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def build(p,out):command([CLANG,*FLAGS,'-Wl,--export=pop_run',p,'-o',out],out.with_suffix('.log'))
def run(out):
 out.mkdir(parents=True,exist_ok=False)
 for n in ['population.c','check.mjs','native.lisp']:shutil.copy(HERE/n,out/n)
 shutil.copy(ROOT/'runtime/wasm32/bootstrap-populations.mjs',out/'builder.mjs')
 (out/'adapter.wat').write_text(adapter());(out/'generated.mjs').write_text(generated());build(out/'population.c',out/'population.wasm')
 command([WABT,'--enable-threads','--enable-exceptions',out/'adapter.wat','-o',out/'adapter.wasm'],out/'adapter.log')
 command([CLANG,*FLAGS,'-Wl,--export=collect',ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],out/'collector.log')
 prior=E/'2026-09-20-stage1-hash-tables-r1/execution';shutil.copytree(prior/'compiled',out/'compiled')
 kernel=E/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=E/'2026-09-16-stage1-1a-r2/native/baseline.image'
 with tempfile.TemporaryDirectory(prefix='ccl-population-native-') as d:
  w=Path(d);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image');command([w/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log')
 native=[l for l in (out/'native.log').read_text().splitlines() if l.startswith('POPULATION|')];assert native==['POPULATION|list|0|copy-spine|member-identity|nil|proper|dotted|cycle|type-refusal','POPULATION|alist|1|copy-spine|member-identity|nil|proper|dotted|cycle|type-refusal'];save(out/'native.json',native)
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 controls=[]
 for name,a,b,why in [
  ('wrong-slot','if(op==0)answer=L(base+8);','if(op==0)answer=L(base+4);','contents'),
  ('no-set','S(base+8,key);','/* no store */','set readback'),
  ('wrong-type','else answer=L(base+4);','else answer=0;','type code'),
  ('no-list-check','if(op==1&&key!=NIL','if(0&&op==1&&key!=NIL','type refusal'),
  ('two-values','S(result+8,1);','S(result+8,2);','publication'),
  ('no-pad-check','||L(base+12)!=0','||0','population pad'),
 ]:
  d=out/'faults'/name;d.mkdir(parents=True)
  for f in ['population.c','population.wasm','collector.wasm','builder.mjs','adapter.wasm','generated.mjs','native.json','check.mjs']:shutil.copy(out/f,d/f)
  shutil.copytree(out/'compiled',d/'compiled');s=(d/'population.c').read_text();assert s.count(a)==1;(d/'population.c').write_text(s.replace(a,b));build(d/'population.c',d/'population.wasm')
  try:command([NODE,d/'check.mjs',d,d/'execution.json'],d/'rejected.log')
  except subprocess.CalledProcessError:
   assert why in (d/'rejected.log').read_text(),name;controls.append(dict(name=name,status='REJECTED',diagnostic=why))
  else:raise AssertionError(name+' escaped')
 save(out/'controls.json',controls)
 paths=[kernel,image,CLANG,NODE,WABT,*[f for f in (prior/'compiled').iterdir() if f.is_file()]];save(out/'inputs.json',{str(p):sha(p) for p in paths})
 rows=json.loads((out/'execution.json').read_text())['rows'];summary=dict(status='PASS',workers=len(rows),comparisons=sum(r['comparisons'] for r in rows),collections=sum(r['collections'] for r in rows),controls=len(controls),slot_credit=False);save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.output.resolve())
