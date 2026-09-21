#!/usr/bin/env python3
import argparse,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import HERE,ROOT,E,parents,sha,read,save,pin_parents
ID='STAGE1-STARTUP-REVIEW-137-R1'
SOURCES=['README.md','derive.py','run.py','equality-probe.mjs','population-probe.mjs','packet.py','development.json']
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def retained(p):
 for f in files(p):
  rel=f.relative_to(p)
  if any(n in rel.parts for n in ['build','installed']):continue
  # Keep changed fault input/binary and rejection, not duplicate prerequisites.
  if len(rel.parts)>2 and rel.parts[0]=='equality' and rel.parts[1]=='faults' and f.name not in ['hash.c','eql.wasm','equal.wasm','rejected.log']:continue
  yield f

def deterministic(p):return {str(f.relative_to(p)):sha(f) for f in retained(p) if f.suffix in ['.json','.mjs','.wasm','.wat','.lisp','.c','.py','.dx64fsl'] and not f.name.endswith('command.json')}
def pins():
 result={}
 for p in parents().values():
  for n,h in read(p/'source-pins.json').items():assert sha(ROOT/n)==h,n;result[n]=h
 for n in SOURCES:result[str((HERE/n).relative_to(ROOT))]=sha(HERE/n)
 return dict(sorted(result.items()))
def dependencies():
 result={}
 for name,p in parents().items():
  for n,h in read(p/'tools.json').items():result[n]=h
  inputs=read(p/('inputs.json' if name=='startup-host-inputs' else 'execution/inputs.json'))
  for n,h in inputs.items():
   path=(E/n if name=='startup-host-inputs' else ROOT/n);result[str(path)]=h
 for n,h in result.items():assert sha(Path(n))==h,n
 return result

def manifest(p):save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--packet',required=True,type=Path);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert read(x/'summary.json')['status']=='PASS';p.mkdir()
  save(p/'source-pins.json',pins());save(p/'dependencies.json',dependencies());save(p/'deterministic.json',deterministic(x))
  for f in retained(x):
   dest=p/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
  for n in ['README.md','development.json']:shutil.copy(HERE/n,p/n)
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in SOURCES:tar.add(HERE/n,arcname=str((HERE/n).relative_to(ROOT)),recursive=False)
  with tarfile.open(p/'development.tar.gz','w:gz') as tar:
   for n in read(HERE/'development.json')['retained']:tar.add(Path('/tmp')/n,arcname=n,recursive=False)
  manifest(p)
 else:
  assert pins()==read(p/'source-pins.json')
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
  assert dependencies()==read(p/'dependencies.json')
  assert pin_parents()==read(p/'execution/parent-bindings.json')
  out=a.output.resolve();out.mkdir()
  with (out/'replay.log').open('w') as log:subprocess.run([sys.executable,HERE/'run.py','--output',out/'execution'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
  got=deterministic(out/'execution');wanted=read(p/'deterministic.json');assert got==wanted,sorted(n for n in got.keys()|wanted.keys() if got.get(n)!=wanted.get(n))
  record=dict(status='PASS',deterministic_files=len(wanted),source_pins=len(pins()),summary=read(out/'execution/summary.json'));save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
