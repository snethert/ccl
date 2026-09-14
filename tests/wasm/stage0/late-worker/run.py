#!/usr/bin/env python3
"""S0-LL13-b: real late Workers preserve live memory and code namespaces."""
import argparse,copy,hashlib,json,platform,shutil,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
from oracle import check,REFUSALS
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];TOOLS=ROOT/'doc/WASM/tools'
sys.path.insert(0,str(TOOLS))
from evidence_binding import bind_report,contract_hash
ID='S0-LL13-b'
SCOPE='Hand-built scalar Wasm on macOS Node/V8: four real Workers, 64 KiB shared memory, emitter-owned static/BSS/heap/staging/private ranges and separate eight-slot per-Worker tables. Explicit process-once and owned private setup, lazy code publication, late/subsequent creation. No C linker/TLS, B compiler, full CCL object layout, GC or browser qualification.'
ACTIVE='  (data (i32.const 64) "BAD!")\n'
START='  (func $bad_start (memory.fill (i32.const 128) (i32.const 0) (i32.const 64)))\n  (start $bad_start)\n'
# Real module/loader mutations, with fresh matching identity manifests. The
# observed refusal must therefore come from initialization policy or behavior.
ATTACKS={
 'active-data':('kernel','\n)\n','\n'+ACTIVE+')\n'),
 'start-bss':('kernel','\n)\n','\n'+START+')\n'),
 'overlap':('kernel','(export "heap_base") i32 (i32.const 8192)','(export "heap_base") i32 (i32.const 128)'),
 'misaligned':('kernel','(export "worker_base") i32 (i32.const 4096)','(export "worker_base") i32 (i32.const 4097)'),
 'undersized':('kernel','(export "tls_size") i32 (i32.const 16)','(export "tls_size") i32 (i32.const 8)'),
 'lazy-data':('lazy','\n)\n','\n'+ACTIVE+')\n'),
 'lazy-start':('lazy','\n)\n','\n'+START+')\n'),
}
# case -> (underlying attack, changed source, old, new, first independent error)
MUTANTS={
 'active-check-omitted':('active-data','late-loader',"if(m.data.some(d=>!d.passive))throw Error('ACTIVE_DATA');",'', 'MEMORY instance-2'),
 'start-check-omitted':('start-bss','late-loader',"if(m.start!==undefined)throw Error('START_FUNCTION');",'', 'MEMORY instance-2'),
 'process-guard-omitted':(None,'kernel','(i32.ne (i32.atomic.rmw.cmpxchg (i32.const 32) (i32.const 0) (i32.const 1)) (i32.const 0))','(i32.const 0)','MEMORY retry-process-2'),
 'wrong-owner':(None,'kernel','    ;; These four ranges','    (local.set $base (i32.const 4096))\n    ;; These four ranges','MEMORY setup-2'),
 'tls-overrun':(None,'kernel','(memory.fill (local.get $base) (i32.const 0) (i32.const 16))','(memory.fill (local.get $base) (i32.const 0) (i32.const 32))','MEMORY setup-2'),
 'tls-clear-omitted':(None,'kernel','(memory.fill (local.get $base) (i32.const 0) (i32.const 16))','(nop)','MEMORY setup-2'),
 'late-install-omitted':(None,'late-loader','table.set(slot,instance.exports.entry);','/* missing table installation */','STATE setup-2'),
 'lazy-start-check-omitted':('lazy-start','loader',"if(m.start!==undefined)throw Error('LAZY_START');",'','MEMORY install-0'),
 'reserved-check-omitted':('lazy-reserved','loader',"if(meta.reserved.includes(slot))throw Error('RESERVED_SLOT');",'','STATE install-0'),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def require(x,r):
 if not x:raise ValueError(r)
def sources():return [HERE/n for n in ('kernel.wat','lazy.wat','abi.json','loader.mjs','worker.mjs','execute.mjs','oracle.py','run.py')]+[HERE.parent/'runtime-boundary/binary.mjs',TOOLS/'gate.py',TOOLS/'evidence_binding.py']
def invoke(argv,commands,out,cwd=None):
 try:p=subprocess.run(argv,cwd=cwd or ROOT,capture_output=True,text=True,timeout=60)
 except subprocess.TimeoutExpired as e:
  commands.append(dict(argv=argv,error=str(e)));save(out/'commands.json',commands);raise
 commands.append(dict(argv=argv,cwd=str(cwd or ROOT),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));save(out/'commands.json',commands)
 require(p.returncode==0,'COMMAND_EXIT '+repr(commands[-1]));return p.stdout

def replace(text,old,new,name):
 require(text.count(old)==1,'MUTANT_SITE '+name);return text.replace(old,new)

def exercise(out):
 require(platform.system()=='Darwin','MACOS_REFERENCE');out.mkdir(parents=True,exist_ok=False)
 node=Path(shutil.which('node')).resolve();compiler=Path(shutil.which('wat2wasm')).resolve();commands=[]
 environment=dict(node=invoke([str(node),'--version'],commands,out).strip(),wabt=invoke([str(compiler),'--version'],commands,out).strip(),
  executable_sha256={str(p):sha(p) for p in (node,compiler)},python=sys.version,platform=platform.platform())
 save(out/'environment.json',environment)
 kernel=(HERE/'kernel.wat').read_text();lazy=(HERE/'lazy.wat').read_text();loader=(HERE/'loader.mjs').read_text()
 observations=[]
 for case in ['complete',*REFUSALS,*MUTANTS]:
  b=out/'bundles'/case;b.mkdir(parents=True);d=out/'cases'/case;d.mkdir(parents=True)
  save(d/'config.json',dict(case=case));texts=dict(kernel=kernel,lazy=lazy,loader=loader);attack_kernel=None;attack_loader=None
  underlying=MUTANTS[case][0] if case in MUTANTS else case
  if underlying in ATTACKS:
   kind,old,new=ATTACKS[underlying];changed=replace(texts[kind],old,new,underlying)
   if kind=='kernel':attack_kernel=changed
   else:texts[kind]=changed
  if case in MUTANTS:
   _,kind,old,new,_=MUTANTS[case]
   if kind=='kernel':attack_kernel=replace(kernel,old,new,case)
   elif kind=='late-loader':attack_loader=replace(loader,old,new,case)
   else:texts[kind]=replace(texts[kind],old,new,case)
   save(b/'mutation.json',dict(case=case,underlying_attack=underlying,kind=kind,old=old,new=new,first_failure=MUTANTS[case][-1]))
  if attack_kernel:texts['attack-kernel']=attack_kernel
  if attack_loader:texts['attack-loader']=attack_loader
  (b/'abi.json').write_bytes((HERE/'abi.json').read_bytes())
  options=dict(compiler_arguments=['--enable-threads'],node_arguments=[],memory_pages=1,workers=4,profile='full')
  save(b/'options.json',options);save(b/'host-compiler.json',dict(path=str(compiler),sha256=sha(compiler),version=environment['wabt']))
  for name,text in texts.items():
   if 'loader' in name:(b/(name+'.mjs')).write_text(text)
   else:
    (b/(name+'.wat')).write_text(text)
    invoke([str(compiler),'--enable-threads',name+'.wat','-o',name+'.wasm'],commands,out,cwd=b)
  slot=0 if underlying=='lazy-reserved' else 2
  save(b/'manifest.json',dict(version=1,slot=slot,attackKernel=bool(attack_kernel),attackLoader=bool(attack_loader),
   files={p.name:sha(p) for p in sorted(b.iterdir()) if p.is_file()}))
  invoke([str(node),str(HERE/'execute.mjs'),str(b),str(d/'config.json'),str(d)],commands,out)
  observed=read(d/'observed.json');require(observed['node']==environment['node'],'ENGINE_IDENTITY')
  if case in MUTANTS:
   try:check(d,b,case)
   except ValueError as e:require(str(e)==MUTANTS[case][-1],'MUTANT_REASON '+case+': '+str(e))
   else:raise ValueError('MUTANT_ESCAPED '+case)
   observations.append(dict(case=case,status='REJECTED_MUTANT',reason=MUTANTS[case][-1]))
  else:observations.append(check(d,b,case))
 save(out/'observations.json',observations)
 save(out/'summary.json',dict(version=1,id=ID,variant='full',status='PASS',scope=SCOPE,review_disposition='NOT_REVIEWED',
  positive_scenarios=1,positive_steps=24,refused_scenarios=len(REFUSALS),semantic_mutants_rejected=len(MUTANTS),
  real_workers=4,shared_memory_bytes=65536,private_regions_per_worker=4,table_slots_per_worker=8))
 return observations

def retain(p,x,replay=False):
 if replay:require(read(p)==x,'RETAINED '+p.name)
 else:save(p,x)
def slot(out,replay=False):
 inv=read(out/'inventory.json');inv['tests']=[t for t in inv['tests'] if t['id']==ID];retain(out/'slot-inventory.json',inv,replay)
 p=subprocess.run([sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(out/'results.json')],capture_output=True,text=True,timeout=30)
 value=dict(exit_code=p.returncode,result=json.loads(p.stdout),stderr=p.stderr)
 require(value==dict(exit_code=2,result=dict(status='BLOCKED',reasons=['unreviewed '+ID+' [full]']),stderr=''),'SLOT_GATE');return value

def omissions(out,replay=False):
 inv=read(out/'slot-inventory.json');base=read(out/'results.json');results=[]
 for role in list(dict.fromkeys(inv['required_record_roles']+inv['tests'][0]['required_record_roles'])):
  report=copy.deepcopy(base);report['results'][0]['artifacts']=[a for a in report['results'][0]['artifacts'] if a['role']!=role]
  p=out/('omit-'+role+'.json');retain(p,report,replay)
  run=subprocess.run([sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(p)],capture_output=True,text=True,timeout=30)
  value=json.loads(run.stdout);require(run.returncode==1 and not run.stderr and value==dict(status='FAIL',reasons=['missing artifact roles: '+ID+' [full]','unreviewed '+ID+' [full]']),'ROLE_OMISSION '+role)
  results.append(dict(role=role,exit_code=run.returncode,result=value))
 retain(out/'role-omissions.json',results,replay)

def run(out):
 require(ROOT not in out.parents and out!=ROOT and not out.exists(),'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
 snapshots={str(p.relative_to(ROOT)):p.read_bytes() for p in sources()}
 record=dict(version=1,status='FAIL',command=[sys.executable,*sys.argv],timestamp=datetime.now(timezone.utc).isoformat(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
 try:
  invpath=ROOT/'doc/WASM/stage0/inventory.json';inv=read(invpath);test=next(t for t in inv['tests'] if t['id']==ID)
  require(test['runner']==str(HERE.relative_to(ROOT)/'run.py'),'RUNNER_REGISTRATION')
  exercise(out);(out/'inventory.json').write_bytes(invpath.read_bytes());(out/'source').mkdir()
  for p in sources():(out/'source'/p.name).write_bytes(p.read_bytes())
  def role(p):
   if p.parent==out/'bundles/complete':
    return {'kernel.wasm':'installed-binary','lazy.wasm':'installed-binary','kernel.wat':'template','lazy.wat':'source','abi.json':'abi','options.json':'options','host-compiler.json':'host-compiler'}.get(p.name,'log')
   if p.name in ('loader.mjs','kernel.wat','lazy.wat'):return 'implementation'
   if p.name in ('oracle.py','execute.mjs','worker.mjs','run.py'):return 'test'
   return 'schema' if p.name in ('inventory.json','abi.json') else 'log'
  artifacts=[dict(path=p.relative_to(out).as_posix(),sha256=sha(p),role=role(p)) for p in sorted(out.rglob('*')) if p.is_file()]
  report=dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,results=[dict(id=ID,variant='full',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',
   assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],artifacts=artifacts,substitutions=[],skips=[],review_disposition='NOT_REVIEWED',
   command=record['command'],toolchain=read(out/'environment.json'),engine='Node/V8 actual Worker instantiation and Wasm execution',timestamp=record['timestamp'],configuration=dict(scope=SCOPE),
   seed='ordered four-Worker schedule; named initialization policy and implementation mutations',test_revision=sha(HERE/'oracle.py'))])
  save(out/'results.json',bind_report(report,inv,'inventory.json',sha(out/'inventory.json')));save(out/'slot-gate.json',slot(out));omissions(out)
  require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
  record.update(status='PASS',contract_sha256=contract_hash(inv,ID));print('PASS: LL13-b, 24 complete transitions, 11 pre-publication refusals, 9 semantic mutants and 10 role omissions. Review pending.')
 except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
 finally:
  if out.exists():
   save(out/'run.json',record);(out/'source').mkdir(exist_ok=True)
   for name,data in snapshots.items():(out/'source'/Path(name).name).write_bytes(data)

def verify(packet):
 record=read(packet/'run.json');require(record['status']=='PASS','RUN_STATUS')
 for name,h in record['source_sha256'].items():require(sha(ROOT/name)==h,'SOURCE_PIN '+name)
 for a in read(packet/'results.json')['results'][0]['artifacts']:require(sha(packet/a['path'])==a['sha256'],'ARTIFACT '+a['path'])
 temp=Path(tempfile.mkdtemp(prefix='ccl-late-worker-verify-'))
 try:
  fresh=temp/'replay';require(exercise(fresh)==read(packet/'observations.json'),'REPLAY_OBSERVATIONS')
  names=[p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name!='commands.json']
  for n in names:require((fresh/n).read_bytes()==(packet/n).read_bytes(),'REPLAY_BYTES '+str(n))
  require(slot(packet,True)==read(packet/'slot-gate.json'),'RETAINED_SLOT');omissions(packet,True)
 except BaseException as e:
  save(temp/'failure.json',dict(status='FAIL',packet=str(packet),source_sha256=record['source_sha256'],error=str(e)))
  print('Original verification failure retained at '+str(temp),file=sys.stderr);raise
 else:shutil.rmtree(temp)
 print('PASS: fresh Worker/Wasm execution; '+str(len(names))+' identical deterministic files, full-memory and instance oracles, direct pins and role refusals.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:verify(a.verify.resolve())
 else:run(a.output.resolve())
