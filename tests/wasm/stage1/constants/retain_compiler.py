#!/usr/bin/env python3
"""Keep the compiler development checkpoint compact; no gate record is produced."""
import argparse,hashlib,json,shutil,tarfile,tempfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def retain(evidence,run,native,archive,development):
    if archive.exists():raise ValueError('no overwrite')
    if read(run/'summary.json')['status']!='PASS':raise ValueError('incomplete verification')
    baseline='2026-09-16-stage1-1a-r2'
    known={r['sha256']:baseline+'/'+r['path'] for r in read(evidence/baseline/'packet.json')['files']}
    with tempfile.TemporaryDirectory(prefix='ccl-pool-retain-') as tmp:
        root=Path(tmp);shutil.copytree(run,root/'verified');(root/'native').mkdir();refs=[]
        for p in sorted(native.rglob('*')):
            if not p.is_file():continue
            dest='native/'+str(p.relative_to(native));h=sha(p)
            if h in known:refs.append({'path':dest,'evidence_path':known[h],'sha256':h})
            else:
                q=root/dest;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,q)
        save(root/'references.json',refs)
        for p in development:
            q=root/'development'/p.name;q.parent.mkdir(parents=True,exist_ok=True)
            if p.is_dir():shutil.copytree(p,q)
            else:shutil.copy(p,q)
        save(root/'manifest.json',{str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()})
        archive.parent.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,'w:gz') as tar:
            for p in sorted(root.rglob('*')):
                if p.is_file():tar.add(p,arcname=str(p.relative_to(root)))
    print(json.dumps({'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size}))
def hydrate(evidence,checkpoint,out):
    row=read(checkpoint);archive=evidence/row['archive']
    if sha(archive)!=row['archive_sha256']:raise ValueError('checkpoint bytes')
    out.mkdir(parents=True,exist_ok=False)
    with tarfile.open(archive) as tar:tar.extractall(out,filter='data')
    for rel,h in read(out/'manifest.json').items():
        p=(out/rel).resolve()
        if not p.is_relative_to(out.resolve()) or sha(p)!=h:raise ValueError('checkpoint member '+rel)
    for r in read(out/'references.json'):
        p=(evidence/r['evidence_path']).resolve();q=(out/r['path']).resolve()
        if not p.is_relative_to(evidence.resolve()) or not q.is_relative_to(out.resolve()):raise ValueError('reference path')
        if q.exists() or sha(p)!=r['sha256']:raise ValueError('reference '+r['path'])
        q.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,q)
    print('CHECKPOINT-HYDRATED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['retain','hydrate']);p.add_argument('--evidence',type=Path,required=True)
    for n in ('run','native','archive','checkpoint','output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args()
    if a.action=='retain':retain(a.evidence,a.run,a.native,a.archive,a.development)
    else:hydrate(a.evidence,a.checkpoint,a.output)
