#!/usr/bin/env python3
"""Retain one final LL10 packet; archive repetitive cases and reference the baseline."""
import argparse,json,shutil,tarfile
from pathlib import Path
from run import read,save,sha,require

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-LL10-R1','scope':'S1-LL10-a generated constant pools; NOT_REVIEWED, not integrated.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})
def archive(directory,destination):
 with tarfile.open(destination,'w:gz') as t:
  for p in sorted(directory.rglob('*')):
   if p.is_file():t.add(p,arcname=str(p.relative_to(directory)))
def retain(evidence,run,native,out,development):
 require(not out.exists(),'NO_OVERWRITE');require(read(run/'summary.json')['status']=='PASS','EXECUTION');out.mkdir(parents=True)
 for p in run.iterdir():
  if p.name in ('inherited','compiler-controls','image-controls'):archive(p,out/(p.name+'.tar.gz'))
  elif p.is_dir():shutil.copytree(p,out/p.name)
  else:shutil.copy(p,out/p.name)
 known={r['sha256']:'2026-09-16-stage1-1a-r2/'+r['path'] for r in read(evidence/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[]
 for p in native.rglob('*'):
  if not p.is_file():continue
  h=sha(p);name='native/'+str(p.relative_to(native))
  if h in known:refs.append({'path':name,'sha256':h,'evidence_path':known[h]})
  else:q=out/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,q)
 save(out/'references.json',refs)
 with tarfile.open(out/'development.tar.gz','w:gz') as t:
  for directory in development:
   if directory.is_file():t.add(directory,arcname=directory.name);continue
   for p in sorted(directory.rglob('*')):
    if p.is_file():t.add(p,arcname=directory.name+'/'+str(p.relative_to(directory)))
 save(out/'earlier-development.json',{'archive':'development-stage1-constants/compiler-r1.tar.gz','sha256':sha(evidence/'development-stage1-constants/compiler-r1.tar.gz'),'scope':'Earlier compiler failures and pre-qualification checkpoint; superseded by this complete packet.'})
 manifest(out)
def hydrate(evidence,packet,dest):
 shutil.copytree(packet,dest)
 for r in read(packet/'references.json'):
  source=(evidence/r['evidence_path']).resolve();target=(dest/r['path']).resolve()
  require(source.is_relative_to(evidence.resolve()) and target.is_relative_to(dest.resolve()) and not target.exists() and sha(source)==r['sha256'],'REFERENCE')
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(source,target)
 for n in ('inherited','compiler-controls','image-controls'):
  with tarfile.open(packet/(n+'.tar.gz')) as t:t.extractall(dest/n,filter='data')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','run','native','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args();retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.output.resolve(),a.development)
