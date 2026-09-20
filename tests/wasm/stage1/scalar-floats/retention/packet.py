"""Retain/replay the complete runtime fix without duplicating reviewed modules."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
from run import ROOT,BASE,FAST,COLLECTOR,sha,read,save,command
ID='STAGE1-SCALAR-FLOATS-R1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins(e):
 r=read(e/FAST/'source-pins.json')
 for n,h in r.items():assert sha(ROOT/n)==h,n
 for f in files(HERE):r[str(f.relative_to(ROOT))]=sha(f)
 return dict(sorted(r.items()))
def inputs(e):
 names=[BASE+'/packet.json',BASE+'/execution.tar.gz',BASE+'/deterministic.json',FAST+'/packet.json',COLLECTOR,'2026-09-19-stage1-float-core-r2/execution/cases.json','2026-09-12-native-census-r7/baseline/build/dx86cl64','2026-09-16-stage1-1a-r2/native/baseline.image']
 p='2026-09-19-stage1-float-owner-r1/execution/'
 names += [p+n for n in ['execute.mjs','inputs.json','float.wasm','detector.wasm','collector.wasm']]
 return {n:sha(e/n) for n in names}
def retained(x):
 for f in files(x):
  n=f.relative_to(x)
  if n.parts[0]=='base':continue
  if n.parts[0]=='generated' and n.name not in ['execute.mjs','scalar-service.mjs','service-inputs.json']:continue
  if n.parts[0].startswith('timing-') and n.name not in ['execution-timing.json','timing.json','benchmark.mjs','execute.mjs','execution.log','timing.log','execution.command.json','timing.command.json','service-loop.wasm']:continue
  if n.parts[0]=='native' and n.name=='dx86cl64':continue
  if n.name in ['cases.json','float.wasm','detector.wasm','collector.wasm']:continue
  yield f,str(n)
def selected(x):
 r={}
 for f,n in retained(x):
  if n.startswith(('native/','timing-','development/')) or f.name in ['timing.json']:continue
  if f.name.endswith('.command.json') or f.suffix=='.log':continue
  r[n]=sha(f)
 return r
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def manifest(p):save(p/'packet.json',dict(id=ID,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS'
 for n,h in read(x/'executed-source-pins.json').items():assert sha(ROOT/n)==h,n
 p.mkdir();save(p/'source-pins.json',pins(e));save(p/'inputs.json',inputs(e));save(p/'deterministic.json',selected(x))
 archive(p/'sources.tar.gz',[(f,str(f.relative_to(ROOT))) for f in files(HERE)])
 archive(p/'execution.tar.gz',retained(x));shutil.copytree(x/'proposal',p/'proposal')
 for n in ['summary.json','controls.json','raw-summary.json','regions.json','timing.json']:shutil.copy(x/n,p/n)
 save(p/'native-reuse.json',dict(compiler_sha256=sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),qualification=BASE+'/native-reuse.json',scope='Unchanged compiler and 76 generated modules reused by reviewed LL16 packet hashes. Independent native functional answers retained there; fresh native timing is compiled and run here. Runtime proposal includes the unintegrated owner fast-path correction in '+FAST+'. No new gate credit.'))
 save(p/'toolchain.json',[dict(path=str(Path(n).resolve()),sha256=sha(Path(n).resolve()),version=subprocess.check_output([n,'--version'],text=True).strip()) for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm']])
 manifest(p)
def verify(e,p,out):
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 assert pins(e)==read(p/'source-pins.json');assert inputs(e)==read(p/'inputs.json')
 for r in read(p/'toolchain.json'):assert sha(Path(r['path']))==r['sha256']
 out.mkdir(parents=True,exist_ok=False)
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys(),(actual.keys()-expected.keys(),expected.keys()-actual.keys())
 for n,h in expected.items():assert actual[n]==h,n
 assert pins(e)==read(p/'source-pins.json')
 save(out/'verification.json',dict(status='PASS',deterministic_files=len(actual),source_pins=len(pins(e)),summary=read(out/'execution/summary.json'),timing='FRESH_MEASUREMENTS_NOT_BYTE_EQUALITY'))
 print((out/'verification.json').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--execution',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
