#!/usr/bin/env python3
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];E=ROOT.parent/'ccl-evidence';P=E/'2026-09-21-stage1-startup-review-138-r1'
NODE=Path('/usr/local/bin/node');CLANG=Path('/usr/local/opt/llvm/bin/clang')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
def bind():
 for n,h in read(P/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for r in read(P/'packet.json')['files']:assert sha(P/r['path'])==r['sha256'],r['path']
 deps=read(P/'dependencies.json')
 for tool in [NODE,CLANG]:assert sha(tool)==deps['TOOL/'+str(tool)]
 return {n:sha(P/n) for n in ['packet.json','source-pins.json','verification.json','dependencies.json']}
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def run(out):
 out.mkdir(parents=True,exist_ok=False);save(out/'parent-binding.json',bind());records=[];services=out/'services';services.mkdir()
 for kind in ['eql','equal','population']:
  source=P/'execution/services'/(kind+'.c');binary=P/'execution/services'/(kind+'.wasm')
  shutil.copy(source,services/source.name);shutil.copy(binary,services/binary.name)
  command([NODE,HERE/'probe.mjs',kind,binary,out/(kind+'.json')],out/(kind+'.log'))
  if kind=='population':
   s=replace(source.read_text(),'!backed(result,16)||','');s=replace(s,'S(result,answer);','if(!backed(result,16))return 1; S(result,answer);')
   faults=[('delayed-result-guard',s,'SET before result validation')]
  else:
   faults=[('component-marker',replace(source.read_text(),'if(k==EMPTY||k==DELETED)return 0;',''),'nested marker')]
   if kind=='equal':faults += [('table-overlap',replace(source.read_text(),'overlap(p,n,b,bytes)||',''),'table overlap'),('static-cons-overlap',replace(source.read_text(),'||overlap(p,n,1048576,65536)',''),'static cons overlap')]
  for name,s,why in faults:
   d=out/'faults'/(kind+'-'+name);d.mkdir(parents=True);f=d/'service.c';f.write_text(s)
   exports=['pop_run'] if kind=='population' else ['__stack_pointer','ht_init','ht_size','ht_run','ht_kind']
   command([CLANG,*FLAGS,*(['-DMODE='+str(1 if kind=='eql' else 2)] if kind!='population' else []),*['-Wl,--export='+x for x in exports],f,'-o',d/'service.wasm'],d/'build.log')
   try:command([NODE,HERE/'probe.mjs',kind,d/'service.wasm',d/'execution.json',why],d/'rejected.log')
   except subprocess.CalledProcessError:assert why in (d/'rejected.log').read_text(),name
   else:raise AssertionError(name+' escaped')
   records.append(dict(service=kind,fault=name,diagnostic=why,status='REJECTED'))
 save(out/'controls.json',records);assert bind()==read(out/'parent-binding.json')
 summary=dict(status='PASS',directed_checks=sum(len(read(out/(k+'.json'))['rows']) for k in ['eql','equal','population']),new_faults=len(records),services_unchanged=True,parent_replay='reused by hash; audit 139 reproduced it',slot_credit=False)
 save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output.resolve())
