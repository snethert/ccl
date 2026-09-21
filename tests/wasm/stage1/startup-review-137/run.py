#!/usr/bin/env python3
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from derive import HERE,ROOT,host,replace
E=ROOT.parent/'ccl-evidence';NODE=Path('/usr/local/bin/node');CLANG=Path('/usr/local/opt/llvm/bin/clang')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,**kw):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200,**kw)
def reject(args,log,why):
 try:command(args,log)
 except subprocess.CalledProcessError:
  assert why in log.read_text(),(why,log.read_text()[-2000:])
 else:raise AssertionError('fault escaped '+why)
def parents():return {name:E/('2026-09-20-stage1-'+name+'-r1') for name in ['startup-host-inputs','equality-tables','population-access']}
def pin_parents():
 result={}
 for name,p in parents().items():
  for n,h in read(p/'source-pins.json').items():assert sha(ROOT/n)==h,n
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
  result[name]={n:sha(p/n) for n in ['packet.json','source-pins.json','verification.json']}
 return result

def run(out):
 out.mkdir(parents=True,exist_ok=False);save(out/'parent-bindings.json',pin_parents());records=[]
 # Native semantic change: Wasm reader branch, then the unchanged native body.
 driver=out/'host-driver';host(driver)
 command([sys.executable,driver/'run.py','--output',out/'host'],out/'host.log',env={**os.environ,'CCL_REVIEW_ROOT':str(ROOT)})
 prior=parents()['startup-host-inputs']/'execution'
 assert all(sha(out/'host/compiled'/p.name)==sha(p) for p in (prior/'compiled').glob('*.wasm'))
 assert not (out/'host/composition.mjs').exists()
 # The new NIL/cons row extends, rather than reindexes, the native matrix.
 driver=out/'equality-driver';driver.mkdir()
 for name in ['derive.py','run.py','faults.py','keys.c','check.mjs','corpus.lisp']:shutil.copy(ROOT/'tests/wasm/stage1/equality-tables'/name,driver/name)
 p=driver/'derive.py';p.write_text(replace(p.read_text(),'ROOT=HERE.parents[3]',"ROOT=Path(__import__('os').environ['CCL_REVIEW_ROOT'])"))
 p=driver/'corpus.lisp';p.write_text(replace(p.read_text(),'#c(1 2) #c(1 2) #c(1 3))))','#c(1 2) #c(1 2) #c(1 3) (cons nil nil))))'))
 p=driver/'check.mjs';p.write_text(replace(p.read_text(),"const service=(await",'put(NIL-1,NIL);put(NIL+3,NIL);\n const service=(await'))
 command([sys.executable,driver/'run.py','--output',out/'equality'],out/'equality.log',env={**os.environ,'CCL_REVIEW_ROOT':str(ROOT)})
 eq=out/'equality';old=parents()['equality-tables']/'execution'
 for n in ['hash.c','eql.wasm','equal.wasm','collector.wasm','adapter.wasm']:assert sha(eq/n)==sha(old/n),n
 oldnative=read(old/'native.json');newnative=read(eq/'native.json');matrix_count=len(oldnative['objects']);assert len(newnative['objects'])==matrix_count+1
 for mode in ['eql','equal']:assert [r[:matrix_count] for r in newnative[mode][:matrix_count]]==oldnative[mode];assert newnative[mode][0][-1]==0 and newnative[mode][-1][0]==0
 shutil.copy(HERE/'equality-probe.mjs',eq/'review-probe.mjs');command([NODE,eq/'review-probe.mjs',eq/'equal.wasm',eq/'review.json'],eq/'review.log')
 for name,a,b,why in [('nil-cons','||a==NIL||b==NIL||a==TRUE||b==TRUE','','NIL versus cons'),('depth','used+2>KEY_DEPTH','0','bounded car depth 1024')]:
  d=eq/'review-faults'/name;d.mkdir(parents=True);s=(eq/'hash.c').read_text();assert s.count(a)==(2 if name=='depth' else 1);s=s.replace(a,b);(d/'hash.c').write_text(s)
  command([CLANG,*FLAGS,'-Wl,--export=__stack_pointer','-DMODE=2',*['-Wl,--export='+x for x in ['ht_init','ht_size','ht_run','ht_kind']],d/'hash.c','-o',d/'equal.wasm'],d/'build.log')
  reject([NODE,eq/'review-probe.mjs',d/'equal.wasm',d/'result.json'],d/'rejected.log',why);records.append(dict(unit='equality',name=name,diagnostic=why))
 # The redundant base alignment predicate is removed only in the derived C;
 # object tag 6 already entails (object-6)%8 == 0. Binary identity is required.
 pop=out/'population';pop.mkdir();old=parents()['population-access']/'execution'
 for n in ['population.c','population.wasm','collector.wasm','builder.mjs','adapter.wasm','generated.mjs','native.json','check.mjs']:shutil.copy(old/n,pop/n)
 shutil.copytree(old/'compiled',pop/'compiled')
 s=replace((pop/'population.c').read_text(),'||(base&7)','');(pop/'population.c').write_text(s)
 def build(source,dest):command([CLANG,*FLAGS,'-Wl,--export=pop_run',source,'-o',dest],dest.with_suffix('.build.log'))
 build(pop/'population.c',pop/'population.wasm');assert sha(pop/'population.wasm')==sha(old/'population.wasm'),'redundant guard binary identity'
 command([NODE,pop/'check.mjs',pop,pop/'execution.json'],pop/'execution.log');assert read(pop/'execution.json')==read(old/'execution.json')
 shutil.copy(HERE/'population-probe.mjs',pop/'review-probe.mjs');command([NODE,pop/'review-probe.mjs',pop/'population.wasm',pop/'review.json'],pop/'review.log')
 for name,a,b,why in [
  ('tag','(object&7)!=6||','','object tag'),('extent','||end!=(W)base+16','','exact extent'),
  ('type-alignment','||(L(base+4)&3)','','type alignment'),('result-alignment','(result&3)||','','result alignment'),
  ('alias','||overlap(base,16,result,16)','','publication alias'),('operation','if(op>2)return 5;','','operation bound')]:
  d=pop/'review-faults'/name;d.mkdir(parents=True);(d/'population.c').write_text(replace(s,a,b));build(d/'population.c',d/'population.wasm')
  reject([NODE,pop/'review-probe.mjs',d/'population.wasm',d/'result.json'],d/'rejected.log',why);records.append(dict(unit='population',name=name,diagnostic=why))
 save(out/'controls.json',records)
 summary=dict(status='PASS',host=read(out/'host/summary.json'),equality=read(eq/'summary.json'),equality_objects=matrix_count+1,equality_new_faults=2,population=read(old/'summary.json'),population_new_refusals=12,population_new_faults=6,slot_credit=False)
 save(out/'summary.json',summary);assert pin_parents()==read(out/'parent-bindings.json');print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.output.resolve())
