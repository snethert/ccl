#!/usr/bin/env python3
"""Retain and replay this isolated service with direct prerequisite pins."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(root):return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
def pins():
 paths=list(HERE.glob('*.*'))+[ROOT/n for n in ['tests/wasm/stage0/float-detection/checked.wat','tests/wasm/stage0/float-detection/ieee.py','compiler/WASM32/wasm32-arch.lisp','level-0/l0-float.lisp','level-0/l0-numbers.lisp','level-0/X86/x86-float.lisp','doc/WASM/contracts/floating-point.v1.md','doc/WASM/stage1/integration-integer-owner.json']]
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths) if p.is_file()}
def deterministic(root):
 return {str(p.relative_to(root)):sha(p) for p in files(root) if p.suffix in ['.wasm','.wat','.c','.mjs','.lisp'] or (p.suffix=='.json' and not p.name.endswith('.command.json')) or p.name in ['native-results.txt','hardware-input.txt','hardware-results.txt']}
def manifest(root):save(root/'packet.json',dict(id='STAGE1-FLOAT-CORE-R2',kind='AUXILIARY_FLOAT_PRIMITIVES',review_disposition='NOT_REVIEWED',files=[dict(path=str(p.relative_to(root)),sha256=sha(p),bytes=p.stat().st_size) for p in files(root) if p.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir()
 source=pins();save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n)
 shutil.copytree(x,p/'execution',ignore=shutil.ignore_patterns('dx86cl64'))
 save(p/'deterministic.json',deterministic(x));shutil.copy(x/'summary.json',p/'summary.json')
 refs=read(x/'native-inputs.json')
 for n in ['2026-09-16-stage1-1a-r2/packet.json','2026-09-16-stage1-1a-r2/native/run.json','2026-09-16-float-detection-r4/packet.json']:refs[n]=sha(e/n)
 save(p/'inputs.json',refs)
 # The original development failures stay in the immutable R1 packet.
 original=e/'2026-09-19-stage1-float-core-r1'
 refs['2026-09-19-stage1-float-core-r1/packet.json']=sha(original/'packet.json')
 save(p/'inputs.json',refs)
 for n in ['float.c','float.wasm','detector.wasm']:
  assert sha(x/n)==sha(original/'execution'/n),('service changed',n)
 save(p/'development.json',dict(supersedes='STAGE1-FLOAT-CORE-R1',audit='31cfb7e3',
  failure='R1 rational oracle lost the sign of negative double values rounded to single zero.',
  correction='Copy source sign whenever the rounded result is zero; signed directed cases and both coercions in the random population.',
  regression='execution/old-oracle-result.json',service_byte_identical=True,
  prior_failures='2026-09-19-stage1-float-core-r1/development.tar.gz'))
 assert source==pins();manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins();assert source==read(p/'source-pins.json'),'source pins'
 for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'execution/toolchain.json')['tools']:assert sha(Path(t['path']))==t['sha256'],t['path']
 args=[sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,args)))
 with (out/'replay.log').open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
 actual=deterministic(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys(),'membership'
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins();result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'));save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
