#!/usr/bin/env python3
import argparse, hashlib, json, shutil, subprocess, tempfile
from pathlib import Path
from derive import generate, owner, ROOT, HERE
E=ROOT.parent/'ccl-evidence'
CLANG=Path('/usr/local/opt/llvm/bin/clang'); NODE=Path('/usr/local/bin/node')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=__stack_pointer']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def build(source,out,mode):
 command([CLANG,*FLAGS,'-DMODE='+str(mode),*['-Wl,--export='+x for x in ['ht_init','ht_size','ht_run','ht_kind']],source,'-o',out],out.with_suffix('.build.log'))
def run(out):
 out.mkdir(parents=True,exist_ok=False)
 (out/'hash.c').write_text(generate());(out/'owner.mjs').write_text(owner())
 for mode,name in [(1,'eql'),(2,'equal')]:build(out/'hash.c',out/(name+'.wasm'),mode)
 command([CLANG,*FLAGS,'-Wl,--export=collect',ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],out/'collector-build.log')
 packet=E/'2026-09-20-stage1-hash-tables-r1/execution'
 shutil.copytree(packet/'compiled',out/'compiled');shutil.copy(packet/'adapter.wasm',out/'adapter.wasm')
 shutil.copy(ROOT/'tests/wasm/stage1/hash-tables/generated.mjs',out/'generated.mjs')
 shutil.copy(HERE/'corpus.lisp',out/'corpus.lisp')
 kernel=E/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=E/'2026-09-16-stage1-1a-r2/native/baseline.image'
 with tempfile.TemporaryDirectory(prefix='ccl-equality-native-') as tmp:
  w=Path(tmp);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image')
  command([w/'dx86cl64','--no-init','--batch','--load',out/'corpus.lisp'],out/'native.log')
 rows=[json.loads(l.split('|',1)[1]) for l in (out/'native.log').read_text().splitlines() if l.startswith('CORPUS|')];assert len(rows)==1
 save(out/'native.json',rows[0])
 shutil.copy(HERE/'check.mjs',out/'check.mjs')
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 save(out/'inputs.json',{str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p):sha(p) for p in [ROOT/'runtime/wasm32/hash.c',ROOT/'runtime/wasm32/collector.c',kernel,image,CLANG,NODE,packet/'adapter.wasm',*sorted((packet/'compiled').glob('*'))] if p.is_file()})
 import faults;faults.run(out)
 rows=json.loads((out/'execution.json').read_text())['rows'];summary=dict(status='PASS',comparisons=sum(r['comparisons'] for r in rows),collections=sum(r['collections'] for r in rows),bootstrap_lookups=sum(sum(b['lookups'] for b in r['bootstrap']) for r in rows),workers=len(rows),slot_credit=False);save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.output.resolve())
