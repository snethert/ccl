"""Replay retained LL16 inputs against a runtime-only proposal, then time both."""
import argparse,hashlib,json,os,shutil,statistics,subprocess,tarfile
from pathlib import Path
from derive import derive,replace,ROOT
HERE=Path(__file__).resolve().parent
BASE='2026-09-20-stage1-numeric-qualification-r1'
COLLECTOR='2026-09-19-stage1-collector-qualification-r1/collector.wasm'
NODE='/usr/local/bin/node'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,log,env=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=env,check=True,timeout=1200)
def run(e,out,timing=True):
 out.mkdir(parents=True,exist_ok=False)
 source={str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.mjs','.lisp']}
 save(out/'executed-source-pins.json',source)
 packet=e/BASE
 for r in read(packet/'packet.json')['files']:assert sha(packet/r['path'])==r['sha256'],r['path']
 for n,h in read(packet/'source-pins.json').items():assert sha(ROOT/n)==h,n
 base=out/'base';base.mkdir()
 with tarfile.open(packet/'execution.tar.gz') as t:t.extractall(base,filter='data')
 for n,h in read(packet/'deterministic.json').items():assert sha(base/n)==h,n
 generated=out/'generated';shutil.copytree(base/'generated',generated)
 derive(out/'proposal')
 for p in (out/'proposal').glob('*.mjs'):shutil.copy(p,generated/p.name)
 for mode in ['eager','cold']:
  command([NODE,generated/'execute.mjs',generated,e/COLLECTOR,generated/'integer.wasm',out/(mode+'.json'),mode],out/(mode+'.log'))
  assert read(out/(mode+'.json'))==read(base/'generated'/(mode+'.json')),mode
 # Test-only scan counter observes calls, not timings, and changes no admission.
 s=(out/'proposal/collector-owner.mjs').read_text()
 instrument=lambda text:replace(text,' #imageSlots(){',' #testScans=0;get testImageScans(){return this.#testScans;}\n #imageSlots(){this.#testScans++;')
 checks=(ROOT/'tests/wasm/stage1/collector-owner/check.mjs').read_text()
 marker='fs.writeFileSync(process.argv[3],'
 checks=replace(checks,marker,(HERE/'owner-checks.mjs').read_text()+'\n'+marker)
 (out/'check.mjs').write_text(checks);(out/'owner.mjs').write_text(instrument(s))
 command([NODE,out/'check.mjs',e/COLLECTOR,out/'owner-checks.json'],out/'owner.log')
 controls=[]
 mutations=[
  ('skip-live',"  this.#validateLive();\n  if(this.#t(52)","  if(this.#t(52)",'fast-allocation-limit'),
  ('scan-fast',"  this.#validateLive();\n  if(this.#t(52)","  this.#validate();\n  if(this.#t(52)",'fast assurance must not enumerate'),
  ('cache-image'," #imageSlots(){", " #imageCache;\n #imageSlots(){if(this.#imageCache)return this.#imageCache.slice();",'image'),
  ('skip-canonical',"need(this.#get(NIL-1)===NIL&&this.#get(NIL+3)===NIL&&this.#get(T-6)===1850,'canonical objects');",'', 'T-header'),
 ]
 for name,a,b,diagnostic in mutations:
  if name=='skip-canonical':assert s.count(a)==2;fault=s.replace(a,b)
  else:fault=replace(s,a,b)
  if name=='cache-image':fault=replace(fault,'  return result;','  this.#imageCache=result.slice();return result;')
  (out/'owner.mjs').write_text(instrument(fault));log=out/(name+'.log')
  try:command([NODE,out/'check.mjs',e/COLLECTOR,out/(name+'.json')],log)
  except subprocess.CalledProcessError:
   assert diagnostic in log.read_text(),name
  else:raise AssertionError('escaped '+name)
  controls.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
 (out/'owner.mjs').write_text(instrument(s))
 raw=out/'raw-owner';raw.mkdir()
 prior=e/'2026-09-19-stage1-float-owner-r1/execution'
 manifest={r['path']:r['sha256'] for r in read(prior.parent/'packet.json')['files']}
 for n in ['cases.json','collector.wasm','float.wasm','detector.wasm','inputs.json','execute.mjs']:
  assert sha(prior/n)==manifest['execution/'+n];shutil.copy(prior/n,raw/n)
 shutil.copy(out/'proposal/collector-owner.mjs',raw/'collector-owner.mjs')
 # The raw-owner corpus predates the Lisp adapter; select the original raw
 # entry for its mathematical expectations. Both entries retain identical ABI.
 service=(out/'proposal/float-service.mjs').read_text().replace('wasm.float_calculate_lisp(', 'wasm.float_calculate(')
 (raw/'float-service.mjs').write_text(service)
 script=(raw/'execute.mjs').read_text()
 anchor="rows.push({name:current,grown:true,resultMoved:true});"
 script=replace(script,anchor,anchor+"\n  current='growth-reuse';owner.ensure=n=>{ensures++;return ensure(n);};put(ROOT+8,get(ROOT+16));put(ROOT+16,N);invoke({...row,expected:{...row.expected,value:'4014000000000000'}});rows.push({name:current,checks:1});")
 (raw/'execute.mjs').write_text(script)
 command([NODE,raw/'execute.mjs',raw,raw/'execution.json'],raw/'execution.log')
 result=read(raw/'execution.json');result['rows']=[r for r in result['rows'] if r['name']!='growth-reuse']
 assert result==read(prior/'execution.json')
 # A stale cached view must fail after actual engine growth, not merely because
 # a string or metadata field changed. Remove corpus rows to reach that case.
 save(raw/'cases.json',[])
 fault=replace(service,'if(cachedView.buffer!==b)cachedView=new DataView(b);','')
 (raw/'float-service.mjs').write_text(fault)
 try:command([NODE,raw/'execute.mjs',raw,raw/'stale-view.json'],raw/'stale-view.log')
 except subprocess.CalledProcessError:
  assert read(raw/'stale-view.json')['case']=='growth-reuse'
 else:raise AssertionError('escaped stale view')
 controls.append(dict(name='stale-float-view',status='REJECTED',diagnostic='growth-reuse'))
 shutil.copy(prior/'cases.json',raw/'cases.json');(raw/'float-service.mjs').write_text(service)
 save(out/'controls.json',controls)
 if timing:benchmark(e,out,base)
 rows=read(out/'eager.json')['rows'];scenarios=[r for r in rows if 'cases' in r]
 save(out/'summary.json',dict(status='PASS',comparisons_per_mode=sum(r['cases'] for r in scenarios),collections=sum(r['moves'] for r in scenarios),growths=sum(r['growths'] for r in scenarios),owner_checks=read(out/'owner-checks.json')['checks'],controls=len(controls),compiler='UNCHANGED; LL16 R6/R6a reused by exact source hash',timing='MEASURED' if timing else 'SKIPPED_EXPLICITLY'))
 assert all(sha(ROOT/n)==h for n,h in source.items())
 print(json.dumps(read(out/'summary.json')),flush=True)
def benchmark(e,out,base):
 results={}
 # The same source, modules, reset and native expected values in both variants.
 # Omit only the test's ensure observer (structuredClone on every call). Keep all
 # production root checks and all frame construction in the timed interval.
 for name in ['baseline','proposal']:
  d=out/('timing-'+name);shutil.copytree(base/'generated',d)
  if name=='proposal':
   for p in (out/'proposal').glob('*.mjs'):shutil.copy(p,d/p.name)
  save(d/'native.json',[r for r in read(d/'native.json') if r['function'].startswith('bench_')])
  s=(base/'benchmark/benchmark-source.mjs').read_text()
  a=s.index(' const originalEnsure=owner.ensure.bind(owner);');b=s.index(' const inputs=',a);s=s[:a]+s[b:]
  s=s.replace('1000);','500);').replace('trial<30','trial<20').replace(',250)',',125)').replace('warmupMs:1000,sampleMs:250','warmupMs:500,sampleMs:125')
  s=s.replace("assert.equal(moves,priorMoves,'benchmark must not collect');", "assert.equal(t(56),A,'benchmark must not collect');")
  s=s.replace('arena reset between invocations;', 'heap reset between invocations; allocation observer removed;')
  (d/'benchmark.mjs').write_text(s)
  command([NODE,d/'benchmark.mjs',d,e/COLLECTOR,d/'integer.wasm',d/'execution.json','eager'],d/'execution.log')
  results[name]=read(d/'execution-timing.json')
 native=out/'native';native.mkdir()
 for n in ['native.lisp','native-forms.lisp']:shutil.copy(HERE/n,native/n)
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 shutil.copy(kernel,native/'dx86cl64');(native/'dx86cl64').chmod(0o755)
 command([native/'dx86cl64','--image-name',image,'--no-init','--batch','--load',native/'native.lisp'],native/'execution.log',dict(os.environ,COST_DIR=str(native)))
 native_rows={}
 for line in (native/'native.tsv').read_text().splitlines()[1:]:
  r=line.split();native_rows.setdefault(r[0],[]).append(float(r[2]))
 table=[]
 for op in ['add','sub','mul','div','single','mixed']:
  r={name:statistics.median(x['checked']['nsPerOperation'] for x in raw['trials'] if x['op']==op) for name,raw in results.items()};n=statistics.median(native_rows[op])
  table.append(dict(workload=op,baseline_ns=r['baseline'],proposal_ns=r['proposal'],native_ns=n,speedup=r['baseline']/r['proposal'],remaining_native_ratio=r['proposal']/n))
 save(out/'timing.json',dict(status='MEASURED',results=table,claim='Single-host descriptive warm cost, no collection in Wasm interval; native includes GC. Full service call, not hardware arithmetic latency. Same observer-free harness for baseline and proposal.',host={k:subprocess.check_output(cmd,text=True).strip() for k,cmd in [('os',['sw_vers']),('cpu',['sysctl','-n','machdep.cpu.brand_string']),('node',[NODE,'--version'])]}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--no-timing',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),not a.no_timing)
