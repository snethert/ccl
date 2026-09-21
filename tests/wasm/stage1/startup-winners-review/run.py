#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
WIN='2026-09-20-stage1-startup-winners-r1';JOIN='2026-09-20-stage1-startup-joined-r1';CONFIG='2026-09-20-stage1-startup-config-r2'
CLANG=Path('/usr/local/opt/llvm/bin/clang');NODE=Path('/usr/local/bin/node')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=__stack_pointer']
SOURCES=('run.py','packet.py','README.md','scope.json')
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def command(args,log,expected_failure=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=240)
 if expected_failure:assert r.returncode!=0 and expected_failure in log.read_text(),log
 else:assert r.returncode==0,log
 return r.returncode
def pins(e):
 result={}
 for name in [WIN,JOIN]:
  for n,h in read(e/name/'source-pins.json').items():
   assert sha(ROOT/n)==h,n
   if n in result:assert result[n]==h
   result[n]=h
 for n in SOURCES:result[str((HERE/n).relative_to(ROOT))]=sha(HERE/n)
 return dict(sorted(result.items()))
def check(e):
 source=pins(e)
 for name in [WIN,JOIN,CONFIG]:
  p=e/name
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 # Clang's executable pin is in the original hash-service qualification.
 for t in read(e/'2026-09-20-stage1-hash-tables-r1/toolchain.json')['tools']:
  assert sha(Path(t['path']))==t['sha256']
 assert any(sha(Path(t['path']))==sha(CLANG) for t in read(e/'2026-09-20-stage1-hash-tables-r1/toolchain.json')['tools'])
 return source
def copy_inputs(src,dest):
 dest.mkdir(parents=True)
 for n in ['adapter.wasm','collector.wasm']:shutil.copy(src/n,dest/n)
 shutil.copytree(src/'compiled',dest/'compiled')
def winners(e,out):
 src=e/WIN/'execution';out.mkdir()
 original=(ROOT/'tests/wasm/stage1/startup-winners/check.mjs').read_text()
 guard=""" // Audit 128: the adapter does not consume all four primitive words.
 // Check a successful raw publication independently before generated calls.
 setup(4);primitive(1,T,28);
 assert.equal(service.ht_run(ht,ht-6+service.ht_size(cap),5,NIL,NIL,SCRATCH,SCRATCH+131072,RESULT),0,'raw clear success');
 assert.deepEqual(Array.from({length:4},(_,i)=>get(RESULT+4*i)),[ht,NIL,1,0],'raw clear publication');
 checkEmpty();
"""
 fixed=replace(original," for(const native of read('compiled/native.json'))",guard+" for(const native of read('compiled/native.json'))")
 (out/'check.mjs').write_text(fixed);shutil.copy(src/'hash.c',out/'hash.c');shutil.copy(src/'hash.wasm',out/'hash.wasm')
 for n in ['adapter.wasm','collector.wasm']:shutil.copy(src/n,out/n)
 shutil.copytree(src/'compiled',out/'compiled')
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 assert (out/'execution.json').read_bytes()==(src/'execution.json').read_bytes()
 faults=[('secondary','S(result+4,found);','S(result+4,op==5?TRUE:found);'),('count','S(result+8,op==0?2:1);','S(result+8,op==5?2:op==0?2:1);'),('rehashed','S(result+12,rehashed);','S(result+12,op==5?1:rehashed);')]
 controls=[]
 for name,old,new in faults:
  m=out/'faults'/name;copy_inputs(src,m);(m/'hash.c').write_text(replace((src/'hash.c').read_text(),old,new))
  command([CLANG,*FLAGS,*['-Wl,--export='+n for n in ['ht_size','ht_init','ht_run']],m/'hash.c','-o',m/'hash.wasm'],m/'build.log')
  (m/'old.mjs').write_text(original);(m/'fixed.mjs').write_text(fixed)
  command([NODE,m/'old.mjs',m,m/'escaped.json'],m/'escaped.log')
  assert (m/'escaped.json').read_bytes()==(src/'execution.json').read_bytes(),'old escape '+name
  command([NODE,m/'fixed.mjs',m,m/'rejected.json'],m/'rejected.log','raw clear publication')
  controls.append(dict(name=name,original='ESCAPED',corrected='REJECTED',diagnostic='raw clear publication',binary=sha(m/'hash.wasm')))
 # Keep the nine already qualified faults observable under the added assertion.
 inherited=[]
 for c in read(src/'controls.json'):
  m=out/'inherited'/c['name'];copy_inputs(src,m);shutil.copy(src/'faults'/c['name']/'hash.wasm',m/'hash.wasm');(m/'check.mjs').write_text(fixed)
  why='raw clear publication' if c['name']=='return-identity' else c['diagnostic']
  command([NODE,m/'check.mjs',m,m/'execution.json'],m/'rejected.log',why)
  inherited.append(dict(name=c['name'],status='REJECTED',diagnostic=why))
 save(out/'controls.json',dict(publication=controls,inherited=inherited,execution_identical=sha(out/'execution.json')))
 return dict(publication_faults=3,original_escapes=3,inherited_faults=9,execution_identical=True)
def ordering(e,out):
 src=e/JOIN/'execution';out.mkdir();shutil.copytree(src/'compiled',out/'compiled')
 for f in src.iterdir():
  if f.is_file() and f.suffix in ['.mjs','.json','.wasm','.html']:shutil.copy(f,out/f.name)
 selection=read(e/CONFIG/'execution/config/selection.json')['callbacks']
 modules={r['name'] for r in read(src/'compiled/modules.json')}
 selected=[r for r in selection if r.get('module') in modules]
 assert len(selected)==18
 assert [(r['group'],r['ordinal']) for r in selected]==sorted((r['group'],r['ordinal']) for r in selected)
 order=['preflight']+[r['module'] for r in selected]+['workload'];assert len(set(order))==20
 s=replace((src/'check.mjs').read_text(),"const sequence=['preflight',...resets.map(r=>r.module),...names.slice(1)];","const sequence="+json.dumps(order)+";")
 (out/'check.mjs').write_text(s)
 save(out/'registry-order.json',dict(namespace='retained startup snapshot; system pointers then user pointers',callbacks=selected,modules=order))
 command([NODE,out/'node.mjs',out,out/'execution.json'],out/'execution.log')
 before=read(src/'execution.json');after=read(out/'execution.json');compared=0
 for a,b in zip(before['rows'],after['rows'],strict=True):
  assert a['base']==b['base']
  for x,y in zip(a['rows'],b['rows'],strict=True):
   for k in ['name','sentinel','initial','resetAnswers','answers','workload']:assert x[k]==y[k],k
   assert [r['name'] for r in y['installed']]==order
   assert {r['name']:r['sha256'] for r in x['installed']}=={r['name']:r['sha256'] for r in y['installed']}
   assert [r['id'] for r in y['events'] if r['event']=='entered']==order
   compared+=1
 tools=read(e/CONFIG/'browser-tools.json')
 for n in ['node','browser','playwright']:assert sha(Path(tools[n]))==tools[n+'_sha256']
 command([NODE,out/'browser.mjs',out,tools['playwright'],tools['browser'],'execute'],out/'browser.log')
 assert (out/'execution.json').read_bytes()==(out/'browser.json').read_bytes()
 result=dict(status='PASS',node_scenarios=compared,browser_scenarios=compared,callbacks=18,installed_modules=20,same_semantics=True,grouped_order=['preflight']+[r['module'] for r in read(src/'resets.json')]+['config_5564','config_6151','config_6150','config_6127','config_5566','workload'],registry_order=order)
 save(out/'comparison.json',result);return result

def run(e,out):
 source=check(e);out.mkdir(parents=True,exist_ok=False)
 w=winners(e,out/'winners');o=ordering(e,out/'ordering')
 assert source==pins(e)
 save(out/'summary.json',dict(status='PASS',winners=w,ordering=o,slot_credit=False,compiler_service_adapter_unchanged=True,native_reuse='Unchanged compiler, reviewed service proposal, generated modules and native oracle reused by hash; harness-only follow-up'))
 print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
