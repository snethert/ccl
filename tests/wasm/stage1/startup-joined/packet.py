#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def retained(p):
 for f in files(p):
  n=f.relative_to(p)
  if any(x in n.parts for x in ['driver','proposal','source','compile-input','installed']):continue
  # A fault needs its changed source/binary, command, outcome, and log; shared
  # execution inputs are reconstructed by run.py rather than copied per fault.
  if 'faults' in n.parts and f.name not in ['hash.c','hash.wasm','execution.log','execution.command.json','hash.log','hash.command.json']:continue
  yield f
def deterministic(p):
 return {str(f.relative_to(p)):sha(f) for f in retained(p) if f.suffix in ['.json','.mjs','.wasm','.wat','.lisp','.dx64fsl'] and f.name!='command.json' and not f.name.endswith('.command.json')}
def inputs(e,here):
 parents=['2026-09-20-stage1-startup-config-r2','2026-09-20-stage1-startup-resets-r1']
 if here.name=='startup-winners':parents+=['2026-09-20-stage1-hash-tables-r1']
 return {name+'/'+n:sha(e/name/n) for name in parents for n in ['packet.json','source-pins.json','verification.json','native-reuse.json']}
def pins(e,here):
 source=read(e/'2026-09-20-stage1-startup-config-r2/source-pins.json')
 for n,h in source.items():assert sha(ROOT/n)==h,n
 extra=list(here.iterdir())
 if here.name=='startup-winners':extra += [ROOT/'tests/wasm/stage1/startup-joined'/n for n in ['compile.py','packet.py']]+[ROOT/'tests/wasm/stage1/hash-tables/check.mjs']
 extra += [ROOT/'runtime/wasm32'/n for n in ['hash.c','hash-adapter.wat','collector.c','config.mjs','browser-config.mjs','bootstrap-install.mjs','bootstrap-schedule.mjs']]
 for f in extra:
  if f.is_file() and f.suffix in ['.py','.mjs','.md','.json','.lisp','.c','.wat']:source[str(f.relative_to(ROOT))]=sha(f)
 return dict(sorted(source.items()))
def manifest(p):
 save(p/'packet.json',dict(id=read(p/'scope.json')['id'],slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),bytes=f.stat().st_size,sha256=sha(f)) for f in files(p) if f.name!='packet.json']))
def run(e,here,out):
 out.mkdir(parents=True,exist_ok=False)
 cmd=[sys.executable,here/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,cmd)))
 with (out/'replay.log').open('w') as log:subprocess.run(list(map(str,cmd)),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
def main(here):
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--execution',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();e=a.evidence.resolve();pack=a.packet.resolve();source=pins(e,here)
 if a.mode=='retain':
  assert not pack.exists();x=a.execution.resolve();assert read(x/'summary.json')['status']=='PASS';pack.mkdir()
  save(pack/'source-pins.json',source);save(pack/'inputs.json',inputs(e,here));save(pack/'deterministic.json',deterministic(x))
  with tarfile.open(pack/'sources.tar.gz','w:gz') as t:
   for n in source:t.add(ROOT/n,arcname=n,recursive=False)
  for f in retained(x):
   dest=pack/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
  for n in ['README.md','scope.json','development.json']:shutil.copy(here/n,pack/n)
  for n in ['native-reuse.json','toolchain.json','browser-tools.json']:shutil.copy(e/'2026-09-20-stage1-startup-config-r2'/n,pack/n)
  assert sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')==read(pack/'native-reuse.json')['compiler_sha256']
  with tarfile.open(pack/'development.tar.gz','w:gz') as t:
   for n in read(here/'development.json')['retained']:t.add(Path('/private/tmp')/n,arcname=n,recursive=False)
  assert pins(e,here)==source;manifest(pack)
 else:
  assert source==read(pack/'source-pins.json')
  for r in read(pack/'packet.json')['files']:assert sha(pack/r['path'])==r['sha256'],r['path']
  for n,h in read(pack/'inputs.json').items():assert sha(e/n)==h,n
  for r in read(pack/'toolchain.json')['tools']:assert sha(Path(r['path']))==r['sha256']
  out=a.output.resolve();run(e,here,out)
  assert deterministic(out/'execution')==read(pack/'deterministic.json'),'deterministic replay'
  assert pins(e,here)==source
  v=dict(status='PASS',deterministic_files=len(read(pack/'deterministic.json')),source_pins=len(source),summary=read(out/'execution/summary.json'),native_R6='REUSED_BY_EXACT_COMPILER_HASH')
  save(out/'verification.json',v);print(v)
if __name__=='__main__':main(Path(__file__).resolve().parent)
