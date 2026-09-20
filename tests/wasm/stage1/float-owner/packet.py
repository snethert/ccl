import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(p):return sorted(x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
def pins():
 paths=list(HERE.glob('*.*'))+[ROOT/n for n in ['runtime/wasm32/float.c','runtime/wasm32/float-detector.wat','runtime/wasm32/collector.c','runtime/wasm32/collector-owner.mjs','compiler/WASM32/wasm32-backend.lisp','doc/WASM/stage1/integration-float-core.json','doc/WASM/contracts/tcr.v2.json','doc/WASM/contracts/floating-point.v1.md']]
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths) if p.is_file()}
def deterministic(p):return {str(f.relative_to(p)):sha(f) for f in files(p) if not f.name.endswith('.command.json') and f.suffix in ['.json','.mjs','.wasm']}
def manifest(p):save(p/'packet.json',dict(id='STAGE1-FLOAT-OWNER-R1',kind='AUXILIARY_COLLECTING_FLOAT_CAPABILITY',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir();source=pins();save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n)
 shutil.copytree(x,p/'execution');shutil.copy(HERE/'float-service.mjs',p/'float-service.mjs');shutil.copy(x/'summary.json',p/'summary.json');save(p/'deterministic.json',deterministic(x))
 refs=read(x/'inputs.json')['evidence']
 for n in ['2026-09-19-stage1-float-core-r2/packet.json','2026-09-19-stage1-float-core-r2/execution/native.json','2026-09-19-stage1-collector-qualification-r1/packet.json']:refs[n]=sha(e/n)
 save(p/'inputs.json',refs)
 with tarfile.open(p/'development.tar.gz','w:gz') as t:
  for run,names in {'ccl-float-owner-r1':['execute.mjs','float-service.mjs','execution.json','execution.log'],'ccl-float-owner-r3':['execute.mjs','float-service.mjs','stale-heap/float-service.mjs','stale-heap/execution.json','stale-heap/execution.log']}.items():
   for n in names:t.add(Path('/tmp')/run/n,arcname=run+'/'+n)
 save(p/'development.json',dict(attempts=[dict(name='r1',failure='Harness memory maximum exceeded accepted collector maximum; engine refused admission.'),dict(name='r3',failure='Expected stale-pointer refusal occurred; control recorder assumed WebAssembly.Exception.message exists. Retain explicit code instead.')],capability_changed=False))
 assert source==pins();manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins();assert source==read(p/'source-pins.json')
 for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 t=read(p/'execution/toolchain.json');assert sha(Path(t['node']))==t['sha256']
 args=[sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,args)))
 with (out/'replay.log').open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
 actual=deterministic(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins();v=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'));save(out/'verification.json',v);print(json.dumps(v,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--execution',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
