#!/usr/bin/env python3
import argparse,shutil,sys,tarfile
from pathlib import Path
from run import HERE,ROOT,PARENT,RESETS,sha,read,save,command
ID='STAGE1-STARTUP-CONFIG-R2'
SOURCES=('derive.py','native-cpu.lisp','regression.py','run.py','packet.py','README.md','scope.json','development.json')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def pins(e):
 source=read(e/PARENT/'source-pins.json')
 for n,h in source.items():assert sha(ROOT/n)==h,n
 for n in SOURCES:source[str((HERE/n).relative_to(ROOT))]=sha(HERE/n)
 return source
def retained(out):
 for f in files(out):
  n=f.relative_to(out)
  if any(p in n.parts for p in ['driver','proposal','source','compile-input']):continue
  if 'faults' in n.parts and f.suffix in ['.mjs','.json','.wasm'] and f.name not in ['config.mjs','browser-config.mjs','config_5566.wasm','command.json']:continue
  if n.parts[0]=='regressions' and f.suffix in ['.mjs','.json','.wasm'] and f.name not in ['config_5566.wasm','reset_5568.wasm','check.mjs','command.json','execution.json']:continue
  yield f
def deterministic(out):return {str(f.relative_to(out)):sha(f) for f in retained(out) if f.suffix in ['.json','.mjs','.wasm','.wat','.lisp','.dx64fsl'] and f.name!='command.json' and not f.name.endswith('.command.json')}
def manifest(p):save(p/'packet.json',dict(id=ID,kind='AUXILIARY_STARTUP_CONFIG_CORRECTION',review_disposition='NOT_REVIEWED',slot_credit=False,files=[dict(path=str(f.relative_to(p)),bytes=f.stat().st_size,sha256=sha(f)) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir();source=pins(e);save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n,recursive=False)
 for f in retained(x):
  dest=p/'execution'/f.relative_to(x);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
 save(p/'deterministic.json',deterministic(x))
 for n in ['summary.json','regressions.json']:shutil.copy(x/n,p/n)
 for n in ['README.md','scope.json','development.json']:shutil.copy(HERE/n,p/n)
 refs={}
 for parent in [PARENT,RESETS]:
  for n in ['packet.json','source-pins.json','verification.json','native-reuse.json']:refs[parent+'/'+n]=sha(e/parent/n)
  refs.update(read(e/parent/'inputs.json'))
 for n in ['native-reuse.json','toolchain.json','browser-tools.json']:shutil.copy(e/PARENT/n,p/n)
 assert sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')==read(p/'native-reuse.json')['compiler_sha256']==sha(x/'config/compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp')
 save(p/'inputs.json',refs)
 with tarfile.open(p/'development.tar.gz','w:gz') as t:
  for a in read(HERE/'development.json')['attempts']:
   for n in a['retained']:t.add(Path('/tmp')/n,arcname=n,recursive=False)
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for r in read(p/'toolchain.json')['tools']:assert sha(Path(r['path']))==r['sha256']
 tools=read(p/'browser-tools.json')
 for n in ['browser','playwright','node']:assert sha(Path(tools[n]))==tools[n+'_sha256']
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 expected=read(p/'deterministic.json');actual=deterministic(out/'execution');assert expected.keys()==actual.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);v=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'),native_R6='REUSED_BY_EXACT_COMPILER_HASH');save(out/'verification.json',v);print(v)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--execution',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
