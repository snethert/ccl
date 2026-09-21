#!/usr/bin/env python3
import argparse,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import HERE,ROOT,PARENT,CONFIG,CLANG,NODE,WABT,SOURCES,pins,sha,read,save
ID='STAGE1-STARTUP-DB-R1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts)
def keep(p):
 for f in files(p):
  n=f.relative_to(p)
  if n.parts[0]=='compile':continue
  if 'faults' in n.parts and ('compiled' in n.parts or f.name=='adapter.wasm'):continue
  if f.name=='compiler.dx64fsl':continue
  yield f
def deterministic(p):return {str(f.relative_to(p)):sha(f) for f in keep(p) if f.suffix in ['.wat','.mjs','.wasm','.json','.c','.lisp'] and not f.name.endswith('command.json')}
def manifest(p):save(p/'packet.json',dict(id=ID,review_disposition='NOT_REVIEWED',slot_credit=False,files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def inputs(e):
 names=[PARENT+'/packet.json',PARENT+'/source-pins.json',CONFIG+'/packet.json',CONFIG+'/native-reuse.json',CONFIG+'/toolchain.json',CONFIG+'/execution/config/compiled/command.json','2026-09-20-stage1-hash-tables-r1/toolchain.json','macos-u1-inputs/pins.json']
 return {n:sha(e/n) for n in names}
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);a=a.parse_args();e=a.evidence.resolve();p=a.packet.resolve();source=pins(e)
 if a.mode=='retain':
  x=a.execution.resolve();assert read(x/'summary.json')['status']=='PASS';p.mkdir()
  save(p/'source-pins.json',source);save(p/'deterministic.json',deterministic(x));save(p/'inputs.json',inputs(e))
  save(p/'tools.json',{str(t):sha(Path(t)) for t in [CLANG,NODE,WABT]})
  # Ancestor sources already have immutable snapshots. Retain only the new unit.
  with tarfile.open(p/'sources.tar.gz','w:gz') as t:
   for n in SOURCES:t.add(HERE/n,arcname=str((HERE/n).relative_to(ROOT)),recursive=False)
  for f in keep(x):
   dest=p/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
  for n in ['README.md','scope.json']:shutil.copy(HERE/n,p/n)
  manifest(p)
 else:
  assert source==read(p/'source-pins.json');assert inputs(e)==read(p/'inputs.json')
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
  for n,h in read(p/'tools.json').items():assert sha(Path(n))==h,n
  out=a.output.resolve();out.mkdir();cmd=[sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,cmd)))
  with (out/'replay.log').open('w') as log:subprocess.run(list(map(str,cmd)),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
  assert deterministic(out/'execution')==read(p/'deterministic.json');assert pins(e)==source
  v=dict(status='PASS',source_pins=len(source),deterministic_files=len(read(p/'deterministic.json')),summary=read(out/'execution/summary.json'));save(out/'verification.json',v);print(v)
if __name__=='__main__':main()
