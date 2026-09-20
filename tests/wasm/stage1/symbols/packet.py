#!/usr/bin/env python3
"""Retain and replay LL09-a using pinned source, native image and toolchain."""
import argparse,json,shutil,sys,tarfile,subprocess
from pathlib import Path
from run import ROOT,HERE,read,save,sha,command
ID='STAGE1-SYMBOLS-R1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def pins():
 paths=set(files(HERE))
 for folder in ['constants','registration','architecture']:
  paths.update(files(HERE.parent/folder))
 for n in ['compiler/WASM32/wasm32-backend.lisp','compiler/WASM32/wasm32-arch.lisp','compiler/X86/X8632/x8632-arch.lisp','compiler/ARM/arm-arch.lisp','compiler/ARM/arm-vinsns.lisp','level-0/nfasload.lisp','level-0/l0-symbol.lisp','level-1/l1-symhash.lisp','library/lispequ.lisp','xdump/xfasload.lisp','doc/WASM/contracts/wasm32-layout.v1.json','doc/WASM/contracts/tcr.v1.json','doc/WASM/contracts/tcr.v2.json','doc/WASM/stage1/integration-ll21a.json','doc/WASM/tools/gate.py','doc/WASM/tools/evidence_binding.py']:
  paths.add(ROOT/n)
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def retained(out):
 for p in files(out):
  n=p.relative_to(out)
  if any(part in ['driver','proposal','source'] for part in n.parts):continue
  if 'mutants' in n.parts and any(part in ['compiled','installed'] for part in n.parts):continue
  yield p

def deterministic(out):
 return {str(p.relative_to(out)):sha(p) for p in retained(out) if p.suffix in ['.json','.mjs','.c','.wat','.wasm','.lisp','.dx64fsl'] and p.name!='command.json' and not p.name.endswith('.command.json')}
def manifest(p):save(p/'packet.json',dict(id=ID,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,out,p):
 assert not p.exists() and read(out/'summary.json')['status']=='PASS';p.mkdir();source=pins();save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n,recursive=False)
 for f in retained(out):
  target=p/'execution'/f.relative_to(out);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,target)
 save(p/'deterministic.json',deterministic(out))
 for n in ['summary.json','assessment.json','controls.json','publication-controls.json']:shutil.copy(out/n,p/n)
 for n in ['scope.json','coverage.json','README.md']:shutil.copy(HERE/n,p/n)
 for n in ['abi-decision.json','abi-binding.json','options.json']:shutil.copy(e/'2026-09-19-stage1-control-r1'/n,p/n)
 save(p/'options.json',dict(profile='single-worker-sealed-packages',table_capacities=[4,128],maximum_capacity=256,maximum_name_length=4096,placements=[4194304,8388608,2147483648],target_hash='FNV1A-UTF32-v1',seed=109))
 refs=read(out/'inputs.json')
 for n in ['macos-u1-inputs/source.tar','macos-u1-inputs/bootstrap.tar.gz','macos-u1-inputs/pins.json','2026-09-20-stage1-materialization-r1/wasm32-backend.lisp','2026-09-20-stage1-materialization-r1/qualification/summary.json','2026-09-20-stage1-materialization-r1/qualification/verification.json','2026-09-20-stage1-ll21a-acceptance-r1/packet.json']:
  refs[n]=sha(e/n)
 save(p/'inputs.json',refs)
 compiler=ROOT/'compiler/WASM32/wasm32-backend.lisp';prior=e/'2026-09-20-stage1-materialization-r1'
 assert sha(compiler)==sha(prior/'wasm32-backend.lisp')==sha(out/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp')
 q=read(prior/'qualification/summary.json');assert q['status']=='PASS'
 save(p/'native-reuse.json',dict(status='PASS',compiler_sha256=sha(compiler),qualification=q,scope='Accepted integrated compiler unchanged; all generated symbol callers and native semantics freshly compiled. R6/R6a reused by exact compiler hash. No shared compiler or upstream kernel edit.'))
 shutil.copy(compiler,p/'wasm32-backend.lisp');shutil.copy(HERE/'symbols.c',p/'symbols.c');shutil.copy(HERE/'image.mjs',p/'image.mjs');shutil.copy(HERE/'adapter.wat',p/'adapter.wat')
 tools=[]
 for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm','/usr/local/opt/llvm/bin/clang']:
  f=Path(n).resolve();tools.append(dict(path=str(f),sha256=sha(f),version=subprocess.check_output([str(f),'--version'],text=True).strip()))
 save(p/'toolchain.json',dict(tools=tools))
 description=read(HERE/'development.json')
 with tarfile.open(p/'development.tar.gz','w:gz') as t:
  for row in description['attempts']:
   for n in row.get('retained',[]):
    f=Path('/tmp')/n;assert f.is_file(),n;t.add(f,arcname=n,recursive=False)
 shutil.copy(HERE/'development.json',p/'development.json')
 assert source==pins();manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins();assert source==read(p/'source-pins.json'),'source pins'
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'toolchain.json')['tools']:assert sha(Path(t['path']))==t['sha256'],t['path']
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 expected=read(p/'deterministic.json');actual=deterministic(out/'execution');assert expected.keys()==actual.keys(),(expected.keys()-actual.keys(),actual.keys()-expected.keys())
 for n,h in expected.items():assert actual[n]==h,n
 if (p/'role-controls.json').exists():
  from publish import role_controls
  assert role_controls(e,read(p/'inventory.json'),read(e/(p.name+'-results.json')),sha(p/'inventory.json'))==read(p/'role-controls.json')
 assert source==pins();v=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'),native_R6='REUSED_BY_EXACT_COMPILER_HASH');save(out/'verification.json',v);print(json.dumps(v,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
