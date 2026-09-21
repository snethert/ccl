#!/usr/bin/env python3
import argparse,shutil,tarfile
from pathlib import Path
import run as r
ID='STAGE1-STARTUP-REVIEW-139-R1'
SOURCES=['run.py','packet.py','probe.mjs','README.md','admission-clauses.json']
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins():
 x=r.read(r.P/'source-pins.json')
 for n,h in x.items():assert r.sha(r.ROOT/n)==h,n
 for n in SOURCES:x[str((r.HERE/n).relative_to(r.ROOT))]=r.sha(r.HERE/n)
 return dict(sorted(x.items()))
def deterministic(p):return {str(f.relative_to(p)):r.sha(f) for f in files(p) if f.suffix in ['.json','.wasm','.c']}
def manifest(p):r.save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=r.sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--packet',required=True,type=Path);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert r.read(x/'summary.json')['status']=='PASS';p.mkdir();r.save(p/'source-pins.json',pins());r.save(p/'deterministic.json',deterministic(x));shutil.copytree(x,p/'execution')
  for n in ['README.md','admission-clauses.json']:shutil.copy(r.HERE/n,p/n)
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in SOURCES:tar.add(r.HERE/n,arcname=str((r.HERE/n).relative_to(r.ROOT)),recursive=False)
  manifest(p)
 else:
  assert pins()==r.read(p/'source-pins.json')
  for row in r.read(p/'packet.json')['files']:assert r.sha(p/row['path'])==row['sha256'],row['path']
  assert r.bind()==r.read(p/'execution/parent-binding.json')
  out=a.output.resolve();r.run(out)
  got=deterministic(out);assert got==r.read(p/'deterministic.json')
  record=dict(status='PASS',deterministic_files=len(got),source_pins=len(pins()),summary=r.read(out/'summary.json'));r.save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
