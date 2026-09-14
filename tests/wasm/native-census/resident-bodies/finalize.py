"""Retain one body-witness packet; reference pristine trees and duplicate exports."""
import argparse
from datetime import datetime,timezone
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
from common import HERE,ROOT,read,save,digest,require


def finalize(run,development,out):
    out.mkdir(parents=True,exist_ok=False);report=read(run/'run.json')
    require(report['status']=='PASS','PRODUCER_STATUS')
    for p,sha in report['source_sha256'].items():require(digest(ROOT/p)==sha,'EXECUTED_SOURCE '+p)
    duplicate=[]
    for p in sorted(run.iterdir()):
        if not p.is_file():continue
        if p.name.startswith('repeat-') and p.suffix=='.gz':
            first=run/p.name.replace('repeat-','first-',1)
            if first.exists() and p.read_bytes()==first.read_bytes():
                duplicate.append(dict(original=p.name,retained_as=first.name,sha256=digest(p)));continue
        shutil.copyfile(p,out/p.name)
    save(out/'duplicate-exports.json',duplicate)
    for name in ('inputs.json','development.md'):shutil.copyfile(HERE/name,out/name)
    paths=set(report['source_sha256'])|{str(p.relative_to(ROOT)) for p in HERE.iterdir() if p.suffix in ('.py','.lisp','.json','.md')}
    save(out/'sources.json',{p:digest(ROOT/p) for p in sorted(paths)})
    members=[];seen={};excluded=[]
    with tarfile.open(out/'development.tar.gz','w:gz') as tar:
        for p in sorted(development.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or run in p.parents:continue
            rel=p.relative_to(development).as_posix()
            # Pristine archive copies are exact pinned inputs, not failed
            # execution artifacts. Keep their commands/exports, not the trees.
            if len(p.relative_to(development).parts)>2 and p.relative_to(development).parts[1]=='ccl':
                continue
            raw=p.read_bytes();sha=digest(p);info=tarfile.TarInfo(rel);info.mode=0o644;info.mtime=0
            if sha in seen:info.type=tarfile.LNKTYPE;info.linkname=seen[sha];tar.addfile(info)
            else:info.size=len(raw);tar.addfile(info,io.BytesIO(raw));seen[sha]=rel
            members.append(dict(path=rel,bytes=len(raw),sha256=sha))
    save(out/'development-members.json',members)
    save(out/'packet.json',dict(version=1,id='NATIVE-RESIDENT-BODIES-R1',review_disposition='NOT_REVIEWED',
        timestamp=datetime.now(timezone.utc).isoformat(),scope=report['summary'],
        implementation_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(out.iterdir()) if p.is_file()]))
    print('Retained',len(list(out.iterdir())),'files;',sum(p.stat().st_size for p in out.iterdir()),'bytes.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','development','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();finalize(a.run.resolve(),a.development.resolve(),a.output.resolve())
