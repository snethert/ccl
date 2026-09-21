#!/usr/bin/env python3
import argparse,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import HERE,ROOT,E,sha,save,read
ID='STAGE1-STARTUP-HOST-INPUTS-R1'
SOURCES=['README.md','run.py','native.lisp','compile.lisp','derive.py','inputs.mjs','owner-check.mjs','controls.py','packet.py','development.json']
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def retained(p):return [f for f in files(p) if 'build' not in f.relative_to(p).parts]
def deterministic(p):return {str(f.relative_to(p)):sha(f) for f in retained(p) if f.suffix in ['.json','.mjs','.wasm','.wat','.lisp','.dx64fsl'] and f.name!='command.json' and not f.name.endswith('.command.json')}
def pins():
 paths=[HERE/n for n in SOURCES]
 paths += list((ROOT/'runtime/wasm32').glob('*.mjs'))+[ROOT/'runtime/wasm32/collector.c']
 paths += [ROOT/n for n in ['compiler/WASM32/wasm32-backend.lisp','compiler/X86/X8632/x8632-arch.lisp','level-1/l1-pathnames.lisp','level-1/l1-unicode.lisp','doc/WASM/contracts/wasm32-layout.v1.json','doc/WASM/contracts/tcr.v1.json','tests/wasm/stage1/startup-joined/compile.py','tests/wasm/stage1/architecture/generate.py']]
 paths += [ROOT/'tests/wasm/stage1/registration'/n for n in ['unit.py','load.lisp','payload/wasm32-backend.lisp','payload/xwasm32-fasload.lisp']]
 paths += [ROOT/'tests/wasm/stage1/constants'/n for n in ['compile.py','compiler.py','export.lisp','encode.py','pool.py']]
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def inputs():
 names=['2026-09-20-stage1-startup-config-r2/'+n for n in ['packet.json','native-reuse.json','browser-tools.json','toolchain.json','execution/config/selection.json']]
 parent=E/'2026-09-20-stage1-startup-joined-r1';manifest={r['path']:r['sha256'] for r in read(parent/'packet.json')['files']}
 for p in files(parent/'execution'):
  relative=p.relative_to(parent/'execution')
  if ('compiled' in relative.parts or p.name in set(read(parent/'execution/assets.json'))|{'assets.json'} or p.suffix in ['.mjs','.wasm','.html']):
   assert sha(p)==manifest['execution/'+str(relative)],p
   names.append('2026-09-20-stage1-startup-joined-r1/execution/'+str(relative))
 names+=['2026-09-20-stage1-startup-joined-r1/packet.json','2026-09-20-stage1-population-access-r1/packet.json','2026-09-20-stage1-population-access-r1/execution/collector.wasm',
 'macos-u1-inputs/pins.json','macos-u1-inputs/source.tar','macos-u1-inputs/bootstrap.tar.gz','2026-09-12-native-census-r7/baseline/build/dx86cl64','2026-09-16-stage1-1a-r2/native/baseline.image']
 return {n:sha(E/n) for n in names}
def tools():
 b=read(E/'2026-09-20-stage1-startup-config-r2/browser-tools.json')
 paths=[Path(b[n]) for n in ['node','browser','playwright']]+[Path('/usr/local/bin/wat2wasm')]
 return {str(p):sha(p) for p in paths}
def manifest(p):save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['retain','verify']);ap.add_argument('--packet',required=True,type=Path);ap.add_argument('--execution',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=a.packet.resolve()
 if a.mode=='retain':
  x=a.execution.resolve();assert read(x/'summary.json')['status']=='PASS';p.mkdir()
  save(p/'source-pins.json',pins());save(p/'inputs.json',inputs());save(p/'tools.json',tools());save(p/'deterministic.json',deterministic(x))
  for f in retained(x):
   dest=p/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
  for n in ['README.md','development.json']:shutil.copy(HERE/n,p/n)
  shutil.copy(E/'2026-09-20-stage1-startup-config-r2/native-reuse.json',p/'native-reuse.json')
  with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
   for n in pins():tar.add(ROOT/n,arcname=n,recursive=False)
  with tarfile.open(p/'development.tar.gz','w:gz') as tar:
   for n in read(HERE/'development.json')['retained']:tar.add(Path('/tmp')/n,arcname=n,recursive=False)
  manifest(p)
 else:
  assert pins()==read(p/'source-pins.json')
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
  for n,h in read(p/'inputs.json').items():assert sha(E/n)==h,n
  assert tools()==read(p/'tools.json')
  out=a.output.resolve();out.mkdir()
  with (out/'replay.log').open('w') as log:subprocess.run([sys.executable,HERE/'run.py','--output',out/'execution'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
  got=deterministic(out/'execution');wanted=read(p/'deterministic.json')
  assert got==wanted,sorted(n for n in got.keys()|wanted.keys() if got.get(n)!=wanted.get(n))
  record=dict(status='PASS',deterministic_files=len(wanted),source_pins=len(pins()),summary=read(out/'execution/summary.json'),native_R6='REUSED_BY_EXACT_COMPILER_HASH');save(out/'verification.json',record);print(record)
if __name__=='__main__':main()
