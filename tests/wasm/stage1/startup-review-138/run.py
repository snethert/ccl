#!/usr/bin/env python3
import argparse,importlib.util,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];PRIOR=HERE.with_name('startup-review-137')
sys.path.insert(0,str(PRIOR))
import run as prior
import packet as prior_packet
from run import E,sha,read,save,command,reject,NODE,CLANG,FLAGS
P=E/'2026-09-21-stage1-startup-review-137-r1'
def bind():
 for n,h in read(P/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for row in read(P/'packet.json')['files']:assert sha(P/row['path'])==row['sha256'],row['path']
 return {n:sha(P/n) for n in ['packet.json','source-pins.json','dependencies.json','deterministic.json','verification.json']}
def dependencies():
 # Logical roots for checkout and evidence inputs; actual tools retain paths.
 result={}
 def add(path,h):
  path=Path(path)
  if path.is_relative_to(ROOT):key='ROOT/'+str(path.relative_to(ROOT))
  elif path.is_relative_to(E):key='EVIDENCE/'+str(path.relative_to(E))
  else:key='TOOL/'+str(path)
  assert sha(path)==h,path
  if key in result:assert result[key]==h
  result[key]=h
 for name,p in prior.parents().items():
  for n,h in read(p/'tools.json').items():add(n,h)
  inputs=read(p/('inputs.json' if name=='startup-host-inputs' else 'execution/inputs.json'))
  for n,h in inputs.items():add((E if name=='startup-host-inputs' else ROOT)/n,h)
 # Bind the old absolute-path record by hash and require identical contents
 # after canonicalizing only the two recorded checkout inputs and evidence.
 legacy={}
 for n,h in read(P/'dependencies.json').items():
  suffix=next((s for s in ['runtime/wasm32/collector.c','runtime/wasm32/hash.c'] if n.endswith('/'+s)),None)
  key='ROOT/'+suffix if suffix else ('EVIDENCE/'+str(Path(n).relative_to(E)) if Path(n).is_relative_to(E) else 'TOOL/'+n)
  legacy[key]=h
 assert result==legacy
 return dict(sorted(result.items()))
def run(out):
 out.mkdir(parents=True);save(out/'parent-binding.json',bind());save(out/'dependencies.json',dependencies())
 prior.run(out/'prior')
 got=prior_packet.deterministic(out/'prior');assert got==read(P/'deterministic.json'),'parent deterministic replay'
 records=[];services=out/'services';services.mkdir()
 for kind in ['eql','equal','population']:
  source=out/'prior'/('population/population.c' if kind=='population' else 'equality/hash.c')
  dest=services/(kind+'.c');shutil.copy(source,dest)
  binary=out/'prior'/('population/population.wasm' if kind=='population' else 'equality/'+kind+'.wasm')
  shutil.copy(binary,services/(kind+'.wasm'))
  command([NODE,HERE/'probe.mjs',kind,binary,out/(kind+'.json')],out/(kind+'.log'))
  faults=(
   [('object-backed','!backed(base,16)||','','object backed'),('result-backed','!backed(result,16)||','','result backed'),('key-backed','||!backed(key-1,8)','','key backed'),('header','||L(base)!=762','','population header'),('type-range','||L(base+4)>4','','population type range'),('padding','||L(base+12)!=0','','population padding'),('key-tag','(key&7)!=1||','','key tag')] if kind=='population' else
   [('number-depth','if(used+2>KEY_DEPTH)return 0;','/* omitted number depth */','number depth'),('cons-span','if(!span(k-1,8))return 0;','','cons span'),('header-span','!span(p,4)||','','header span'),('static-header','||overlap(p,4,1048576,65536)','','static opaque header')]+([('cons-depth','||used+2>KEY_DEPTH','','cons depth')] if kind=='equal' else []))
  for name,a,b,why in faults:
   d=out/'faults'/(kind+'-'+name);d.mkdir(parents=True);s=source.read_text();assert s.count(a)==1,(kind,a);s=s.replace(a,b);f=d/'service.c';f.write_text(s)
   exports=['pop_run'] if kind=='population' else ['__stack_pointer','ht_init','ht_size','ht_run','ht_kind']
   command([CLANG,*FLAGS,*(['-DMODE='+str(1 if kind=='eql' else 2)] if kind!='population' else []),*['-Wl,--export='+x for x in exports],f,'-o',d/'service.wasm'],d/'build.log')
   reject([NODE,HERE/'probe.mjs',kind,d/'service.wasm',d/'execution.json',why],d/'rejected.log',why)
   records.append(dict(service=kind,fault=name,diagnostic=why,status='REJECTED'))
 save(out/'controls.json',records)
 assert bind()==read(out/'parent-binding.json')
 summary=dict(status='PASS',parent_deterministic_files=len(got),parent_source_pins=len(read(P/'source-pins.json')),dependencies=len(dependencies()),directed_checks=sum(len(read(out/(k+'.json'))['rows']) for k in ['eql','equal','population']),new_faults=len(records),binaries_unchanged=True,slot_credit=False)
 save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output.resolve())
