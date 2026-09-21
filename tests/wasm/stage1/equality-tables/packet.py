#!/usr/bin/env python3
import argparse,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import HERE,ROOT,E,sha,save,CLANG,NODE
ID='STAGE1-EQUALITY-TABLES-R1'
SOURCES=['README.md','keys.c','derive.py','corpus.lisp','check.mjs','faults.py','run.py','packet.py']
def read(p):return json.loads(p.read_text())
def pins():
 paths=[HERE/n for n in SOURCES]+[ROOT/n for n in ['runtime/wasm32/hash.c','runtime/wasm32/collector.c','runtime/wasm32/bootstrap-tables.mjs','tests/wasm/stage1/hash-tables/generated.mjs','compiler/WASM32/wasm32-backend.lisp','compiler/WASM32/wasm32-arch.lisp','level-0/ARM/arm-pred.lisp','lisp-kernel/arm-spentry.s','xdump/hashenv.lisp']]
 return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def files(p):return [f for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
def deterministic(p):return {str(f.relative_to(p)):sha(f) for f in files(p) if f.suffix in ['.json','.mjs','.c','.wasm','.wat','.lisp'] and not f.name.endswith('command.json')}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--packet',required=True,type=Path);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert read(x/'summary.json')['status']=='PASS';p.mkdir()
  save(p/'source-pins.json',pins());save(p/'deterministic.json',deterministic(x));save(p/'tools.json',{str(t):sha(t) for t in [CLANG,NODE]})
  for f in files(x):
   dst=p/'execution'/f.relative_to(x);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in SOURCES:tar.add(HERE/n,arcname=str((HERE/n).relative_to(ROOT)),recursive=False)
  shutil.copy(HERE/'README.md',p/'README.md')
  save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p)]))
 else:
  assert pins()==read(p/'source-pins.json')
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
  for n,h in read(p/'tools.json').items():assert sha(Path(n))==h,n
  for n,h in read(p/'execution/inputs.json').items():assert sha(ROOT/n)==h,n
  out=a.output.resolve();out.mkdir()
  with (out/'replay.log').open('w') as f:subprocess.run([sys.executable,HERE/'run.py','--output',out/'execution'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
  assert deterministic(out/'execution')==read(p/'deterministic.json');record=dict(status='PASS',files=len(read(p/'deterministic.json')),pins=len(pins()),summary=read(out/'execution/summary.json'));save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
