#!/usr/bin/env python3
"""Retain the audit-103 derivative without modifying the reviewed base packet."""
import argparse,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[3]
spec=importlib.util.spec_from_file_location('integer_parent_packet',BASE/'packet.py');parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
sha=parent.sha;read=parent.read;save=parent.save;files=parent.files
PARENT='2026-09-19-stage1-integer-core-r1';IDENT='STAGE1-INTEGER-REVIEW-R1'
def pins(e):
 result=read(e/PARENT/'source-pins.json')
 for n,h in result.items():assert sha(ROOT/n)==h,n
 result.update({str(p.relative_to(ROOT)):sha(p) for p in HERE.glob('*.*') if p.is_file()})
 return result
def manifest(p):save(p/'packet.json',dict(id=IDENT,kind='AUXILIARY_INTEGER_REVIEW_FOLLOWUP',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir();source=pins(e);save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n)
 shutil.copytree(x,p/'execution',ignore=shutil.ignore_patterns('dx86cl64'))
 save(p/'deterministic.json',parent.deterministic(x));shutil.copy(x/'summary.json',p/'summary.json')
 refs=read(e/PARENT/'inputs.json')
 for n in ['packet.json','source-pins.json','execution/integer.wasm','execution/cases.json']:refs[PARENT+'/'+n]=sha(e/PARENT/n)
 save(p/'inputs.json',refs);assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'execution/execution/toolchain.json')['tools']:assert sha(Path(t['path']))==t['sha256'],t['path']
 args=[sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,args)))
 with (out/'replay.log').open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
 actual=parent.deterministic(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'));save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
