#!/usr/bin/env python3
"""Immutable supplemental packet; the reviewed R1 and its gate row stay intact."""
import argparse,importlib.util,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('symbols_followup_runner',HERE/'run.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
ROOT=runner.ROOT;PARENT=runner.PARENT;sha=runner.sha;save=runner.save;read=runner.read
ID='STAGE1-SYMBOLS-REVIEW-R1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def pins(e):
 source=read(e/PARENT/'source-pins.json')
 for n,h in source.items():assert sha(ROOT/n)==h,n
 source.update({str(p.relative_to(ROOT)):sha(p) for p in files(HERE)})
 return source

def retained(out):
 for f in files(out):
  n=f.relative_to(out)
  if any(x in n.parts for x in ['driver','proposal','source']):continue
  if n.parts[0]=='controls' and any(x in n.parts for x in ['compiled','installed']):continue
  if n.parts[:2]==('directed','compiled'):continue
  if 'mutants' in n.parts and any(x in n.parts for x in ['compiled','installed']):continue
  yield f

def deterministic(out):return {str(p.relative_to(out)):sha(p) for p in retained(out) if p.suffix in ['.json','.c','.mjs','.wasm','.wat','.lisp','.dx64fsl'] and not p.name.endswith('.command.json') and p.name!='command.json'}
def manifest(p):save(p/'packet.json',dict(id=ID,kind='AUXILIARY_SYMBOLS_REVIEW_FOLLOWUP',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir();source=pins(e);save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n,recursive=False)
 for f in retained(x):
  target=p/'execution'/f.relative_to(x);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,target)
 save(p/'deterministic.json',deterministic(x))
 for n in ['summary.json','controls.json','assessment.json']:shutil.copy(x/n,p/n)
 for n in ['README.md','scope.json','development.json']:shutil.copy(HERE/n,p/n)
 shutil.copy(x/'inherited/symbols.c',p/'symbols.c');shutil.copy(x/'inherited/symbols.wasm',p/'symbols.wasm')
 refs=read(e/PARENT/'inputs.json')
 for n in ['packet.json','source-pins.json','execution/symbols.wasm','execution/adapter.wasm','native-reuse.json']:
  refs[PARENT+'/'+n]=sha(e/PARENT/n)
 save(p/'inputs.json',refs);shutil.copy(e/PARENT/'toolchain.json',p/'toolchain.json');shutil.copy(e/PARENT/'native-reuse.json',p/'native-reuse.json')
 with tarfile.open(p/'development.tar.gz','w:gz') as t:
  for a in read(HERE/'development.json')['attempts']:
   for n in a.get('retained',[]):
    f=Path('/tmp')/n;assert f.is_file(),n;t.add(f,arcname=n,recursive=False)
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'toolchain.json')['tools']:assert sha(Path(t['path']))==t['sha256']
 runner.command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 actual=deterministic(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);v=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'));save(out/'verification.json',v);print(v)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
