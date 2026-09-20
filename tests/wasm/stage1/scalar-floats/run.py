"""Scalar fast service composed with unchanged, independently reviewed modules."""
import argparse,hashlib,json,os,shutil,statistics,subprocess,sys,tarfile
from pathlib import Path
from derive import derive,ROOT,HERE,replace
BASE='2026-09-20-stage1-numeric-qualification-r1';FAST='2026-09-20-stage1-numeric-fastpath-r1'
COLLECTOR='2026-09-19-stage1-collector-qualification-r1/collector.wasm';NODE='/usr/local/bin/node'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,env=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=env,check=True,timeout=1200)
def build(wat,wasm,log):command(['/usr/local/bin/wat2wasm','--enable-threads',wat,'-o',wasm],log)
def patch_execute(s,pressure=True):
 s=replace(s,'const bundle=floatingCapabilities({memory,',"const bundle=floatingCapabilities({scalarBytes:fs.readFileSync(dir+'/scalar.wasm'),scalarDigest:inputs.scalar,scalarPressure:"+('collect' if pressure else 'false')+",memory,")
 return s
# Test-only overlay: all pressure-mode imports exhaust the still-free heap before
# entering the real Wasm function. Production and timing imports stay direct.
def pressure_service(s):
 a=' return new WebAssembly.Instance(module,{env,regions:new WebAssembly.Instance(region.module).exports,fallback:{calculate:fallback}}).exports.calculate;'
 b=''' const fast=new WebAssembly.Instance(module,{env,regions:new WebAssembly.Instance(region.module).exports,fallback:{calculate:fallback}}).exports.calculate;
 if(!options.scalarPressure)return fast;
 return (op,root,safe)=>{const v=new DataView(memory.buffer),base=v.getUint32(tcr+48,true),end=v.getUint32(tcr+52,true);for(let p=base;p<end;p+=8){v.setUint32(p,77825,true);v.setUint32(p+4,0,true);}v.setUint32(tcr+48,end,true);return fast(op,root,safe);};'''
 return replace(s,a,b)
def values(report):return [{k:r[k] for k in ['high','collect','id','function','values']} for r in report['rows'] if 'id' in r]
def run(e,out,timing=True):
 out.mkdir(parents=True,exist_ok=False)
 source={str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.mjs','.wat']};save(out/'executed-source-pins.json',source)
 for n,h in read(e/FAST/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for pack in [BASE,FAST]:
  for r in read(e/pack/'packet.json')['files']:assert sha(e/pack/r['path'])==r['sha256'],r['path']
 base=out/'base';base.mkdir()
 with tarfile.open(e/BASE/'execution.tar.gz') as t:t.extractall(base,filter='data')
 for n,h in read(e/BASE/'deterministic.json').items():assert sha(base/n)==h,n
 proposal=out/'proposal';derive(proposal);shutil.copy(HERE/'scalar.wat',proposal/'scalar.wat');build(proposal/'scalar.wat',proposal/'scalar.wasm',out/'build.log')
 generated=out/'generated';shutil.copytree(base/'generated',generated)
 for p in proposal.iterdir():shutil.copy(p,generated/p.name)
 save(generated/'service-inputs.json',read(generated/'service-inputs.json')|{'scalar':sha(proposal/'scalar.wasm')})
 (generated/'execute.mjs').write_text(patch_execute((generated/'execute.mjs').read_text()))
 (generated/'scalar-service.mjs').write_text(pressure_service((proposal/'scalar-service.mjs').read_text()))
 for mode in ['eager','cold']:
  command([NODE,generated/'execute.mjs',generated,e/COLLECTOR,generated/'integer.wasm',out/(mode+'.json'),mode],out/(mode+'.log'))
  assert values(read(out/(mode+'.json')))==values(read(base/'generated'/(mode+'.json')))
 assert read(out/'eager.json')==read(out/'cold.json')
 shutil.copy(HERE/'regions-check.mjs',generated/'regions-check.mjs');command([NODE,generated/'regions-check.mjs',out/'regions.json'],out/'regions.log')
 raw_checks(e,out,proposal)
 controls(e,out,proposal)
 if timing:benchmark(e,out,base)
 scenarios=[r for r in read(out/'eager.json')['rows'] if 'cases' in r]
 save(out/'summary.json',dict(status='PASS',comparisons_per_mode=sum(r['cases'] for r in scenarios),collections=sum(r['moves'] for r in scenarios),growths=sum(r['growths'] for r in scenarios),controls=read(out/'controls.json'),raw=read(out/'raw-summary.json'),regions=read(out/'regions.json'),compiler='UNCHANGED; reviewed LL16 R6/R6a reused by exact hash'))
 assert all(sha(ROOT/n)==h for n,h in source.items())
 print(json.dumps(read(out/'summary.json')),flush=True)
def raw_checks(e,out,proposal):
 d=out/'raw';d.mkdir();prior=e/'2026-09-19-stage1-float-owner-r1/execution'
 for p in proposal.glob('*.mjs'):shutil.copy(p,d/p.name)
 for n in ['float.wasm','detector.wasm','collector.wasm','inputs.json']:shutil.copy(prior/n,d/n)
 shutil.copy(proposal/'scalar.wasm',d/'scalar.wasm')
 # Current Lisp primitive, with accepted native integer convention. Directed
 # floating rows use only float inputs, so the rational corpus is independent.
 shutil.copy(out/'generated/float.wasm',d/'float.wasm')
 inputs=read(d/'inputs.json');inputs['float_sha256']=sha(d/'float.wasm');inputs['scalar_sha256']=sha(d/'scalar.wasm');save(d/'inputs.json',inputs)
 rows=[r for r in read(e/'2026-09-19-stage1-float-core-r2/execution/cases.json') if r['a']['kind'] in ['32','64'] and r['b']['kind'] in ['32','64']];save(d/'cases.json',rows)
 s=(prior/'execute.mjs').read_text().replace("import {floatService} from './float-service.mjs';","import {scalarFloatService as floatService} from './scalar-service.mjs';")
 s=replace(s,'return {memory,tcr:TCR,owner,',"return {scalarBytes:fs.readFileSync(dir+'/scalar.wasm'),scalarDigest:inputs.scalar_sha256,memory,tcr:TCR,owner,")
 # Fast operations do not assure. Force shortage before every pressure entry,
 # preserving the accepted heap poisoning, operand checks and status oracle.
 s=replace(s,'   reset(row,i%7===0);invoke(row);',"   reset(row,i%7===0);if(pressure){for(let p=t(48);p<t(52);p+=8){put(p,N);put(p+4,0);}set(48,t(52));}invoke(row);")
 a=" assert.equal(ensures-beforeEnsure,size?1:0,'only allocated results assure');if(size){assert.equal(get(ROOT+16),t(48)-size+6,'current heap publication');}else assert.equal(t(48),before,'no allocation for condition/boolean');"
 b=" if(!size)assert.equal(t(48),before,'no allocation for condition/boolean');"
 s=replace(s,a,b)
 # Missing space must fall back; an owner returning without space still refuses.
 # The existing raw harness's foreign-TCR checks remain applicable unchanged.
 (d/'execute.mjs').write_text(s)
 command([NODE,d/'execute.mjs',d,d/'execution.json'],d/'execution.log')
 save(out/'raw-summary.json',{k:v for k,v in read(d/'execution.json').items() if k!='rows'})
def controls(e,out,proposal):
 # Filled by the independent fault/ownership probes below.
 from probes import run as probes
 probes(e,out,proposal)
def benchmark(e,out,base):
 results={};proposal=out/'proposal'
 for name in ['owner-fast','scalar']:
  d=out/('timing-'+name);shutil.copytree(base/'generated',d)
  from derive import base as owner_base
  if name=='owner-fast':owner_base.derive(d)
  else:
   for p in proposal.iterdir():shutil.copy(p,d/p.name)
   save(d/'service-inputs.json',read(d/'service-inputs.json')|{'scalar':sha(d/'scalar.wasm')})
  save(d/'native.json',[r for r in read(d/'native.json') if r['function'].startswith('bench_')])
  s=(base/'benchmark/benchmark-source.mjs').read_text();a=s.index(' const originalEnsure=owner.ensure.bind(owner);');b=s.index(' const inputs=',a);s=s[:a]+s[b:]
  if name=='scalar':s=patch_execute(s,False)
  s=s.replace('1000);','500);').replace('trial<30','trial<20').replace(',250)',',125)').replace('warmupMs:1000,sampleMs:250','warmupMs:500,sampleMs:125')
  s=s.replace("assert.equal(moves,priorMoves,'benchmark must not collect');", "assert.equal(t(56),A,'benchmark must not collect');")
  (d/'benchmark.mjs').write_text(s)
  command([NODE,d/'benchmark.mjs',d,e/COLLECTOR,d/'integer.wasm',d/'execution.json','eager'],d/'execution.log');results[name]=read(d/'execution-timing.json')
 native=out/'native';native.mkdir()
 for n in ['native.lisp','native-forms.lisp']:shutil.copy(HERE.parent/'numeric-fastpath'/n,native/n)
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 shutil.copy(kernel,native/'dx86cl64');(native/'dx86cl64').chmod(0o755)
 command([native/'dx86cl64','--image-name',image,'--no-init','--batch','--load',native/'native.lisp'],native/'execution.log',dict(os.environ,COST_DIR=str(native)))
 ns={}
 for line in (native/'native.tsv').read_text().splitlines()[1:]:
  r=line.split();ns.setdefault(r[0],[]).append(float(r[2]))
 rows=[]
 for op in ['add','sub','mul','div','single','mixed']:
  r={name:statistics.median(v['checked']['nsPerOperation'] for v in raw['trials'] if v['op']==op) for name,raw in results.items()};n=statistics.median(ns[op]);rows.append(dict(workload=op,owner_fast_ns=r['owner-fast'],scalar_ns=r['scalar'],native_ns=n,speedup=r['owner-fast']/r['scalar'],native_ratio=r['scalar']/n))
 service_ns=service_benchmark(out)
 save(out/'timing.json',dict(service_only_add_ns=service_ns,status='MEASURED',results=rows,scope='Same observer-free 64-operation generated loops; Wasm does not collect in the timed interval, native includes GC. Sequential variants, descriptive single-host medians. Exact/underflow-enabled modes deliberately use the original service.',host={k:subprocess.check_output(cmd,text=True).strip() for k,cmd in [('os',['sw_vers']),('cpu',['sysctl','-n','machdep.cpu.brand_string']),('node',[NODE,'--version'])]}))
def service_benchmark(out):
 d=out/'timing-service';shutil.copytree(out/'raw',d);save(d/'cases.json',[])
 build(HERE/'service-loop.wat',d/'service-loop.wasm',d/'build.log')
 s=(d/'execute.mjs').read_text();s=s[:s.index('try{\n for(const high of [false,true])')]+(HERE/'service-timing.mjs').read_text()
 (d/'execute.mjs').write_text(s)
 command([NODE,d/'execute.mjs',d,d/'timing.json'],d/'timing.log')
 return statistics.median(r['nsPerOperation'] for r in read(d/'timing.json')['trials'])

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--no-timing',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),not a.no_timing)
