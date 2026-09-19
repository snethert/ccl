#!/usr/bin/env python3
"""Retain and replay audit 88 follow-up without another unchanged R6 build."""
import argparse,json,tarfile,shutil,subprocess,sys
from pathlib import Path
from run import ROOT,HERE,run,read,save,sha

def files(d):
 return [p for p in sorted(d.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
def pins():
 paths=files(HERE)+[ROOT/'doc/WASM/contracts/tcr.v1.json',ROOT/'doc/WASM/contracts/tcr.v2.json',ROOT/'level-1/l1-readloop-lds.lisp']
 return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def archive(path,rows):
 with tarfile.open(path,'w:gz') as t:
  for p,name in rows:t.add(p,arcname=name,recursive=False)
def deterministic(p):
 return p.suffix in ('.wasm','.wat','.dx64fsl') or p.name in ('summary.json','controls.json','native.json','native-condition-classes.json','cases.json','execution.json','refusals.json','tcr.v2.json','root-ir.json','root-contracts.json','modules.json')
def retain(evidence,execution,out):
 assert not out.exists();assert read(execution/'summary.json')['status']=='PASS';out.mkdir()
 save(out/'source-pins.json',pins());archive(out/'sources.tar.gz',[(ROOT/n,n) for n in pins()])
 accepted=evidence/'2026-09-19-stage1-control-r1'
 save(out/'inputs.json',{n:sha(accepted/n) for n in ('packet.json','source-pins.json','wasm32-backend.lisp')})
 archive(out/'execution.tar.gz',[(p,str(p.relative_to(execution))) for p in files(execution)])
 for name in ('summary.json','controls.json','tcr.v2.json'):shutil.copy(execution/name,out/name)
 failures=[]
 for n in (1,2):
  d=Path('/tmp')/('ccl-control-followup-r'+str(n));assert d.is_dir()
  failures += [(p,d.name+'/'+str(p.relative_to(d))) for p in files(d)]
  p=Path(str(d)+'.log');failures.append((p,p.name))
 for n in ('control-followup-first-run.py','control-followup-native-before.lisp'):
  p=Path('/tmp')/n;failures.append((p,'source-at-failure/'+n))
 archive(out/'development.tar.gz',failures)
 save(out/'development.json',{'attempts':[{'id':'r1','result':'FAIL','reason':'Oracle anchor occurs twice; corrected to replace only the native condition-suite branch.'},{'id':'r2','result':'FAIL','reason':'CCL kernel function redefinition guard refused the private native observer; bind its warning policy off in that disposable session.'},{'id':'r3','result':'PASS'}],'scope':'Original generated harnesses, inputs and logs retained. Neither failure ran a changed Wasm compiler.'})
 save(out/'packet.json',{'id':'STAGE1-CONTROL-FOLLOWUP-R1','review_disposition':'NOT_REVIEWED','files':[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files(out)]})
def verify(evidence,packet,out):
 for r in read(packet/'packet.json')['files']:
  p=(packet/r['path']).resolve();assert p.is_relative_to(packet.resolve()) and sha(p)==r['sha256'],r['path']
 assert read(packet/'source-pins.json')==pins(),'follow-up sources'
 accepted=evidence/'2026-09-19-stage1-control-r1'
 for name,h in read(packet/'inputs.json').items():assert sha(accepted/name)==h,name
 run(evidence,out);count=0
 with tarfile.open(packet/'execution.tar.gz') as t:
  for m in t.getmembers():
   if deterministic(Path(m.name)):
    assert t.extractfile(m).read()==(out/m.name).read_bytes(),m.name;count+=1
 assert read(packet/'source-pins.json')==pins()
 save(out/'verification.json',{'status':'PASS','deterministic_files':count,'source_pins':len(pins()),'compiler':'unchanged accepted LL19; R6/R6a reused'})
 print(json.dumps(read(out/'verification.json')))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['retain','verify']);p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--execution',type=Path);p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.action=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
