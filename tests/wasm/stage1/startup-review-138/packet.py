#!/usr/bin/env python3
import argparse,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review138',HERE/'run.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
ID='STAGE1-STARTUP-REVIEW-138-R1'
SOURCES=['run.py','packet.py','probe.mjs','README.md','admission-clauses.json','development.json']
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins():
 x=r.read(r.P/'source-pins.json')
 for n,h in x.items():assert r.sha(r.ROOT/n)==h,n
 for n in SOURCES:x[str((HERE/n).relative_to(r.ROOT))]=r.sha(HERE/n)
 return dict(sorted(x.items()))
def retained(p):
 for f in files(p):
  if 'prior' not in f.relative_to(p).parts:yield f
 # Parent bytes are already retained; keep only hashes and summary here.
def deterministic(p):return {str(f.relative_to(p)):r.sha(f) for f in retained(p) if f.suffix in ['.json','.wasm','.c']}
def manifest(p):r.save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=r.sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--packet',required=True,type=Path);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert r.read(x/'summary.json')['status']=='PASS';p.mkdir();r.save(p/'source-pins.json',pins());r.save(p/'dependencies.json',r.dependencies());r.save(p/'deterministic.json',deterministic(x))
  for f in retained(x):
   dest=p/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
  for n in ['README.md','admission-clauses.json','development.json']:shutil.copy(HERE/n,p/n)
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in SOURCES:tar.add(HERE/n,arcname=str((HERE/n).relative_to(r.ROOT)),recursive=False)
  with tarfile.open(p/'development.tar.gz','w:gz') as tar:
   for n in r.read(HERE/'development.json')['retained']:tar.add(Path('/tmp')/n,arcname=n,recursive=False)
  manifest(p)
 else:
  assert pins()==r.read(p/'source-pins.json');assert r.dependencies()==r.read(p/'dependencies.json')
  for row in r.read(p/'packet.json')['files']:assert r.sha(p/row['path'])==row['sha256'],row['path']
  out=a.output.resolve();out.mkdir()
  r.command([sys.executable,HERE/'run.py','--output',out/'execution'],out/'replay.log')
  got=deterministic(out/'execution');assert got==r.read(p/'deterministic.json'),sorted(n for n in got.keys()|r.read(p/'deterministic.json').keys() if got.get(n)!=r.read(p/'deterministic.json').get(n))
  record=dict(status='PASS',deterministic_files=len(got),source_pins=len(pins()),summary=r.read(out/'execution/summary.json'));r.save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
