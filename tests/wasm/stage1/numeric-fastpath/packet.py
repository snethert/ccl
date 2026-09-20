"""Retain only this proposal and its outputs; inputs remain in reviewed packs."""
import argparse,shutil,sys,tarfile
from pathlib import Path
from run import ROOT,HERE,BASE,COLLECTOR,read,save,sha,command
ID='STAGE1-NUMERIC-FASTPATH-R1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins(e):
 r=read(e/BASE/'source-pins.json')
 for n,h in r.items():assert sha(ROOT/n)==h,n
 for f in files(HERE):r[str(f.relative_to(ROOT))]=sha(f)
 return dict(sorted(r.items()))
def inputs(e):
 names=[BASE+'/packet.json',BASE+'/execution.tar.gz',BASE+'/deterministic.json',COLLECTOR,'2026-09-12-native-census-r7/baseline/build/dx86cl64','2026-09-16-stage1-1a-r2/native/baseline.image']
 prefix='2026-09-19-stage1-float-owner-r1/'
 names+=[prefix+'packet.json']+[prefix+'execution/'+n for n in ['cases.json','collector.wasm','float.wasm','detector.wasm','inputs.json','execute.mjs','execution.json']]
 return {n:sha(e/n) for n in names}
def selected(x):
 names=['executed-source-pins.json','summary.json','controls.json','owner-checks.json','check.mjs','owner.mjs','eager.json','cold.json','raw-owner/execution.json','raw-owner/stale-view.json']
 names+=['proposal/'+n for n in ['collector-owner.mjs','float-service.mjs','service.mjs']]
 return {n:sha(x/n) for n in names}
def retained(x):
 for f in files(x):
  n=f.relative_to(x)
  if n.parts[0] in ['base','generated']:continue
  if n.parts[0].startswith('timing-') and f.name not in ['execution.json','execution-timing.json','execution.log','execution.command.json','benchmark.mjs','native.json']:continue
  if f.name=='dx86cl64':continue
  if n.parts[0]=='raw-owner' and f.name in ['collector.wasm','float.wasm','detector.wasm','cases.json','inputs.json']:continue
  yield f,str(n)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def manifest(p):save(p/'packet.json',dict(id=ID,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists();assert read(x/'summary.json')['status']=='PASS'
 for n,h in read(x/'executed-source-pins.json').items():assert sha(ROOT/n)==h,n
 p.mkdir();save(p/'source-pins.json',pins(e));save(p/'inputs.json',inputs(e));save(p/'deterministic.json',selected(x))
 archive(p/'sources.tar.gz',[(f,str(f.relative_to(ROOT))) for f in files(HERE)])
 archive(p/'execution.tar.gz',retained(x))
 for n in ['summary.json','controls.json','owner-checks.json','timing.json']:shutil.copy(x/n,p/n)
 shutil.copytree(x/'proposal',p/'proposal')
 save(p/'native-reuse.json',dict(compiler_sha256=sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),qualification=BASE+'/native-reuse.json',scope='Compiler and generated modules unchanged. Retained native functional answers reused by complete packet and input hashes; native timing freshly compiled and executed. No new LL16 credit.'))
 manifest(p)
def verify(e,p,out):
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 assert pins(e)==read(p/'source-pins.json')
 assert inputs(e)==read(p/'inputs.json')
 out.mkdir(parents=True,exist_ok=False)
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 assert selected(out/'execution')==read(p/'deterministic.json')
 assert pins(e)==read(p/'source-pins.json')
 save(out/'verification.json',dict(status='PASS',deterministic_files=len(selected(out/'execution')),source_pins=len(pins(e)),summary=read(out/'execution/summary.json'),timing='FRESH_MEASUREMENTS_NOT_BYTE_EQUALITY'))
 print((out/'verification.json').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--execution',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
