import argparse,hashlib,json,shutil,subprocess,tempfile,os
from pathlib import Path
from derive import HERE,ROOT,sources,replace
E=ROOT.parent/'ccl-evidence';P=E/'2026-09-21-stage1-population-consumers-r1';S=E/'2026-09-21-stage1-startup-review-138-r1'
NODE=Path('/usr/local/bin/node');CLANG=Path('/usr/local/opt/llvm/bin/clang')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,**kw):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300,**kw)
def build(p,kind):
 command([CLANG,*FLAGS,*['-Wl,--export='+x for x in (['collect','__stack_pointer'] if kind=='collector' else ['pop_run'])],p/(kind+'.c'),'-o',p/(kind+'.wasm')],p/(kind+'-build.log'))
def run(out):
 out.mkdir(parents=True,exist_ok=False)
 for parent in [P,S]:
  for n,h in read(parent/'source-pins.json').items():assert sha(ROOT/n)==h,n
  for row in read(parent/'packet.json')['files']:assert sha(parent/row['path'])==row['sha256']
 save(out/'parent-bindings.json',{parent.name:{n:sha(parent/n) for n in ['packet.json','source-pins.json','verification.json']} for parent in [P,S]})
 deps=read(P/'execution/dependencies.json')
 for t in [NODE,CLANG]:assert sha(t)==deps['TOOL/'+str(t)]
 save(out/'tools.json',{str(t):sha(t) for t in [NODE,CLANG]})
 for n,s in sources(S).items():(out/n).write_text(s)
 for kind in ['collector','population']:build(out,kind)
 for n in ['sha256.mjs','bytes.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['shape.mjs','image.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['check.mjs','install.mjs','adapter.wasm','native.json']:shutil.copy(P/'execution'/n,out/n)
 shutil.copytree(P/'execution/compiled',out/'compiled')
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 assert read(out/'execution.json')==read(P/'execution/execution.json'),'unchanged native observations'
 command([NODE,out/'shape.mjs',out,out/'shape.json'],out/'shape.log');command([NODE,out/'image.mjs',out,out/'image.json'],out/'image.log')
 shutil.copy(ROOT/'tests/wasm/stage1/collector-owner/check.mjs',out/'owner-check.mjs');command([NODE,out/'owner-check.mjs',out/'collector.wasm',out/'owner.json'],out/'owner.log')
 controls=[]
 for name,filename,a,b,script,only,why in [
  ('collector-count','collector.c','n!=2||','','shape.mjs','native-three','native-three'),
  ('collector-extent','collector.c','||(W)p+16>s->used','','shape.mjs','truncated','truncated'),
  ('collector-type','collector.c','(LOAD(p+4)!=0&&LOAD(p+4)!=4)','0','shape.mjs','type-flags','type-flags'),
  ('collector-padding','collector.c','(LOAD(p+4)!=0&&LOAD(p+4)!=4)||LOAD(p+12)!=0','(LOAD(p+4)!=0&&LOAD(p+4)!=4)','shape.mjs','padding','padding'),
  ('collector-data-root','collector.c','scan=2;size=16;','scan=1;size=16;','check.mjs',None,'result tag'),
  ('owner-count','owner.mjs','n===2&&','','image.mjs','native-three','native-three'),
  ('owner-extent','owner.mjs','&&p+16<=region.end','','image.mjs','truncated','truncated'),
  ('owner-type','owner.mjs','[0,4].includes(this.#get(p+4))','true','image.mjs','type-flags','type-flags'),
  ('owner-padding','owner.mjs','&&this.#get(p+12)===0','','image.mjs','padding','padding'),
  ('owner-data-root','owner.mjs','count=2;bytes=16;','count=1;bytes=16;','image.mjs','moving','image contents root moves'),
  ('old-builder-header','builder.mjs','2*256+90','2*256+250','shape.mjs','identity','typed builder'),
  ('old-service-header','population.c','L(base)!=602','L(base)!=762','shape.mjs','identity','typed service')]:
  d=out/'faults'/name;d.mkdir(parents=True)
  for f in out.iterdir():
   if f.is_file() and f.suffix in ['.mjs','.wasm','.c'] or f.name=='native.json':shutil.copy(f,d/f.name)
  shutil.copytree(out/'compiled',d/'compiled')
  (d/filename).write_text(replace((out/filename).read_text(),a,b))
  if filename.endswith('.c'):build(d,filename[:-2])
  args=[NODE,d/script,d,d/'result.json']+([only] if only else [])
  try:command(args,d/'rejected.log')
  except subprocess.CalledProcessError:assert why in (d/'rejected.log').read_text(),(name,(d/'rejected.log').read_text()[-1800:])
  else:raise AssertionError(name+' escaped')
  controls.append(dict(name=name,diagnostic=why,status='REJECTED'))
 save(out/'controls.json',controls)
 save(out/'layout.json',dict(id='strong-population-v2',subtag=90,header_count=2,header=602,bytes=16,type_offset=4,data_offset=8,padding_offset=12,type_words=[0,4],native_weak_counts=[3,4],retention='strong',ordinary_vector_header=762,automatic_conversion=False))
 summary=dict(status='PASS',generated_modules=len(read(out/'compiled/modules.json')),native_cases=len(read(out/'native.json')),native_comparisons=64,generated_collections=80,shape_checks=len(read(out/'shape.json')['rows']),image_checks=len(read(out/'image.json')['rows']),owner_checks=len(read(out/'owner.json')['rows']),faults=len(controls),compiler_unchanged=True,slot_credit=False)
 save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output.resolve())
