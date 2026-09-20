"""Warm, paired generated-call cost; no ABI ranking or production speed claim."""
import json,math,random,statistics,subprocess
from pathlib import Path
from ll16_driver import read,save,command,sha,ROOT

def run(e,out):
 d=out/'generated';dest=out/'benchmark';dest.mkdir()
 s=(d/'execute.mjs').read_text()
 old="[{high:false,collect:false},{high:false,collect:true},{high:true,collect:false},{high:true,collect:true}]"
 assert s.count(old)==1;s=s.replace(old,'[{high:false,collect:false}]')
 marker=' rows.push({high,collect,cases:native.length,ensures,moves,growths,modules:mods.length});';assert s.count(marker)==1
 bench=r'''
 const trials=[], workloads=['add','sub','mul','div','single','mixed'];let state=161613;
 const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296;};
 const measure=(name,ms)=>{
  const c=native.find(c=>c.function===name);assert(c);set(200,7);
  const reset=()=>{set(48,t(56));set(64,ROOT+8);set(128,ROOT);set(120,OUT);set(124,OUT+64);set(140,0);set(148,0);set(192,0);set(76,196608);store(ROOT+4,2);c.args.forEach((v,i)=>store(ROOT+8+4*i,encode(v)));};
  let count=0,last,started=performance.now(),now=started;
  do{for(let j=0;j<8;j++){reset();last=entries[name](handles[name],2);count++;}now=performance.now();}while(now-started<ms);
  assert.equal(last[1],1);assert.deepEqual([decode(get(OUT))],c.expected,name);
  assert.equal(t(128),ROOT);assert.equal(t(64),ROOT+8);assert.equal(moves,priorMoves,'benchmark must not collect');
  return {function:name,milliseconds:now-started,calls:count,operations:count*64,nsPerOperation:(now-started)*1e6/(count*64)};
 };
 const priorMoves=moves;
 for(const op of workloads)for(const suffix of ['', '__unchecked'])measure('bench_'+op+suffix,1000);
 for(let trial=0;trial<30;trial++){
  const order=workloads.map(op=>({op,key:random()})).sort((a,b)=>a.key-b.key).map(x=>x.op);
  for(const op of order){const modes=random()<0.5?['checked','unchecked']:['unchecked','checked'];const row={trial,op,order:modes};for(const mode of modes)row[mode]=measure('bench_'+op+(mode==='unchecked'?'__unchecked':''),250);trials.push(row);}
 }
 fs.writeFileSync(output.replace(/\.json$/, '-timing.json'),JSON.stringify({seed:161613,node:process.version,v8:process.versions.v8,argv:process.execArgv,placement:A,loopOperations:64,warmupMs:1000,sampleMs:250,trials,scope:'Warm eager generated calls; full roots, staging, private service, allocation and return; arena reset between invocations; no collection or cold-install cost. Host argument/reset overhead included in both modes.'},null,2)+'\n');
'''
 s=s.replace(marker,bench+marker);p=dest/'execute.mjs';p.write_text(s)
 # Relative runtime imports resolve from the generated directory.
 shutil_code=dest/'benchmark-source.mjs';shutil_code.write_text(s);target=d/'benchmark.mjs';target.write_text(s)
 command(['/usr/local/bin/node',target,d,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',d/'integer.wasm',dest/'execution.json','eager'],dest/'execution.log')
 raw=read(dest/'execution-timing.json');group={}
 for r in raw['trials']:
  for mode in ['checked','unchecked']:
   v=r[mode];assert v['milliseconds']>=250 and v['operations']==64*v['calls'] and v['calls']>0
  group.setdefault(r['op'],[]).append(r['checked']['nsPerOperation']/r['unchecked']['nsPerOperation'])
 assert len(group)==6 and all(len(rs)==30 for rs in group.values())
 rng=random.Random(161613);stats=[]
 for name,ratios in group.items():
  samples=sorted(math.exp(sum(math.log(rng.choice(ratios)) for _ in ratios)/len(ratios)) for _ in range(10000))
  values=[r for r in raw['trials'] if r['op']==name]
  stats.append(dict(workload=name,paired_trials=30,checked_ns=statistics.median(r['checked']['nsPerOperation'] for r in values),unchecked_ns=statistics.median(r['unchecked']['nsPerOperation'] for r in values),geometric_ratio=math.exp(statistics.mean(map(math.log,ratios))),interval95=[samples[250],samples[9749]]))
 host={}
 for key,args in [('os',['sw_vers']),('cpu',['sysctl','-n','machdep.cpu.brand_string']),('architecture',['uname','-m'])]:host[key]=subprocess.check_output(args,text=True).strip()
 save(dest/'host.json',host)
 save(dest/'summary.json',dict(status='MEASURED',raw_sha256=sha(dest/'execution-timing.json'),trials=len(raw['trials']),results=stats,scope=raw['scope'],claim='Descriptive checking cost on this host/engine. No statistical superiority, ABI choice, representative application or cross-engine claim.'))
