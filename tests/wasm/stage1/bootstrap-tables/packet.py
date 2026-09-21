#!/usr/bin/env python3
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import ROOT,HERE,sha,save
from selection import FILES
def read(p):return json.loads(p.read_text())
ID='STAGE1-BOOTSTRAP-TABLES-R1'
SOURCES=['README.md','selection.py','policy.mjs','check.mjs','run.py','packet.py']
def pins():
 paths=[HERE/n for n in SOURCES]+[ROOT/n for n in FILES+['runtime/wasm32/hash.c','runtime/wasm32/collector.c','level-0/l0-hash.lisp','xdump/hashenv.lisp']]
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
def kept(p):
 for f in sorted(p.rglob('*')):
  if not f.is_file() or '__pycache__' in f.parts:continue
  n=f.relative_to(p)
  if n.parts[0]=='compile':continue
  if 'faults' in n.parts and ('compiled' in n.parts or f.name in ['check.mjs','collector.wasm','hash.wasm','selection.json']):continue
  if n.parts[0]=='compiled' and (f.suffix not in ['.wat','.wasm','.json'] or f.name=='command.json'):continue
  yield f
def deterministic(p):return {str(f.relative_to(p)):sha(f) for f in kept(p) if f.suffix in ['.json','.mjs','.wat','.wasm'] and not f.name.endswith('.command.json')}
def inputs(e):
 return {n:sha(e/n) for n in ['2026-09-12-native-census-r7/baseline/build/dx86cl64','2026-09-16-stage1-1a-r2/native/baseline.image']}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();e=a.evidence.resolve();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert read(x/'summary.json')['status']=='PASS';p.mkdir()
  save(p/'source-pins.json',pins());save(p/'inputs.json',inputs(e));save(p/'deterministic.json',deterministic(x))
  for f in kept(x):
   dst=p/'execution'/f.relative_to(x);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in SOURCES:tar.add(HERE/n,arcname=str((HERE/n).relative_to(ROOT)),recursive=False)
  shutil.copy(HERE/'README.md',p/'README.md')
  save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(p.rglob('*')) if f.is_file()]))
 else:
  assert pins()==read(p/'source-pins.json');assert inputs(e)==read(p/'inputs.json')
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
  for n,h in read(p/'execution/tools.json').items():assert sha(Path(n))==h,n
  out=a.output.resolve();out.mkdir();cmd=[sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,cmd)))
  with (out/'replay.log').open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
  assert deterministic(out/'execution')==read(p/'deterministic.json');assert pins()==read(p/'source-pins.json')
  record=dict(status='PASS',files=len(read(p/'deterministic.json')),pins=len(pins()),summary={k:v for k,v in read(out/'execution/summary.json').items() if k!='rows'});save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
