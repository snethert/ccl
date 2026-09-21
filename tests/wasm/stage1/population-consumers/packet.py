#!/usr/bin/env python3
import argparse,shutil,tarfile
from pathlib import Path
import run as r
ID='STAGE1-POPULATION-CONSUMERS-R1'
SOURCES=['run.py','packet.py','consumers.lisp','lower.lisp','compile.lisp','native.lisp','check.mjs','install.mjs','README.md','development.json']
P=r.E/'2026-09-21-stage1-startup-review-138-r1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins():
 x=r.read(P/'source-pins.json')
 for n,h in x.items():assert r.sha(r.ROOT/n)==h,n
 for n in SOURCES:x[str((r.HERE/n).relative_to(r.ROOT))]=r.sha(r.HERE/n)
 for n in ['tests/wasm/stage1/startup-joined/compile.py','runtime/wasm32/bootstrap-populations.mjs']:
  if n in x:assert r.sha(r.ROOT/n)==x[n]
  else:x[n]=r.sha(r.ROOT/n)
 return dict(sorted(x.items()))
def retained(p):
 for f in files(p):
  rel=f.relative_to(p)
  if 'build' in rel.parts or f.name=='command.json':continue
  if rel.parts[0]=='faults' and f.name in ['check.mjs','install.mjs','builder.mjs','adapter.wasm','collector.wasm','population.wasm','native.json']:continue
  yield f

def deterministic(p):return {str(f.relative_to(p)):r.sha(f) for f in retained(p) if f.suffix in ['.json','.wasm','.wat','.lisp','.mjs','.dx64fsl']}
def manifest(p):r.save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=r.sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--packet',required=True,type=Path);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert r.read(x/'summary.json')['status']=='PASS';p.mkdir();r.save(p/'source-pins.json',pins());r.save(p/'deterministic.json',deterministic(x))
  for f in retained(x):
   dest=p/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
  for n in ['README.md','development.json']:shutil.copy(r.HERE/n,p/n)
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in SOURCES:tar.add(r.HERE/n,arcname=str((r.HERE/n).relative_to(r.ROOT)),recursive=False)
  with tarfile.open(p/'development.tar.gz','w:gz') as tar:
   for n in r.read(r.HERE/'development.json')['retained']:tar.add(Path('/tmp')/n,arcname=n,recursive=False)
  manifest(p)
 else:
  assert pins()==r.read(p/'source-pins.json')
  for row in r.read(p/'packet.json')['files']:assert r.sha(p/row['path'])==row['sha256'],row['path']
  out=a.output.resolve();r.run(out)
  got=deterministic(out);wanted=r.read(p/'deterministic.json');assert got==wanted,sorted(n for n in got.keys()|wanted.keys() if got.get(n)!=wanted.get(n))
  record=dict(status='PASS',deterministic_files=len(got),source_pins=len(pins()),summary=r.read(out/'summary.json'));r.save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
