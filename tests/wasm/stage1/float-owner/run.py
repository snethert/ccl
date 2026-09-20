import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 base=e/'2026-09-19-stage1-float-core-r2';gc=e/'2026-09-19-stage1-collector-qualification-r1'
 pins={}
 for pack,paths in [(base,['execution/float.wasm','execution/detector.wasm','execution/cases.json','execution/float.c','execution/detector.wat']),(gc,['collector.wasm'])]:
  manifest={r['path']:r['sha256'] for r in read(pack/'packet.json')['files']}
  for name in paths:
   assert sha(pack/name)==manifest[name],name;pins[str((pack/name).relative_to(e))]=manifest[name]
 for a,b in [('float.c','float.c'),('float-detector.wat','detector.wat')]:assert sha(ROOT/'runtime/wasm32'/a)==sha(base/'execution'/b)
 for name in ['float.wasm','detector.wasm']:shutil.copy(base/'execution'/name,out/name)
 shutil.copy(gc/'collector.wasm',out/'collector.wasm');shutil.copy(ROOT/'runtime/wasm32/collector-owner.mjs',out/'collector-owner.mjs')
 for name in ['execute.mjs','float-service.mjs']:shutil.copy(HERE/name,out/name)
 population=read(base/'execution/cases.json');rows=[]
 for i,r in enumerate(population):
  if i%157==0 or r['name'].startswith('signed-single-') or (r['name'].startswith('random-coerce-') and int(r['name'].split('-')[2])<30):rows.append(r)
 save(out/'cases.json',rows);save(out/'inputs.json',dict(float_sha256=sha(out/'float.wasm'),detector_sha256=sha(out/'detector.wasm'),collector_sha256=sha(out/'collector.wasm'),evidence=pins))
 save(out/'toolchain.json',dict(node=str(Path('/usr/local/bin/node').resolve()),sha256=sha(Path('/usr/local/bin/node').resolve())))
 command(['/usr/local/bin/node',out/'execute.mjs',out,out/'execution.json'],out/'execution.log')
 import controls;controls.run(out,sys.modules[__name__])
 result=read(out/'execution.json');assert result['status']=='PASS'
 save(out/'summary.json',dict(status='PASS',cases=len(rows),comparisons=result['comparisons'],collections=result['collections'],growths=result['growths'],checks=len(result['rows']),mutants=len(read(out/'controls.json')),compiler_unchanged=True,gate_credit=False))
 print(json.dumps(read(out/'summary.json'),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
