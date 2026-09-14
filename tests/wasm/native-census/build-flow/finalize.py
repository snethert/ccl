"""Retain one build-flow packet and the original development refusals."""
import argparse
from datetime import datetime, timezone
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
from run import ROOT,HERE,read,save,digest
from flow import require


def finalize(run,development,output):
    output.mkdir(parents=True,exist_ok=False)
    summary=read(run/'summary.json')
    require(summary['completed'] and summary['integration']['structural_contract']=='PASS'
            and summary['integration']['closure']=='BLOCKED','RUN_COMPLETION')
    for p,sha in read(run/'run.json')['source_sha256'].items():require(digest(ROOT/p)==sha,'EXECUTED_SOURCE '+p)
    names=('functions.json.gz','calls.json.gz','samples.json.gz','delta.json.gz','summary.json','controls.json',
           'callback-capture.json.gz','run.json')
    for name in names:shutil.copyfile(run/name,output/name)
    shutil.copyfile(HERE/'inputs.json',output/'inputs.json')
    shutil.copyfile(HERE/'development.md',output/'development.md')
    paths=set(read(run/'run.json')['source_sha256'])
    paths.update(str(p.relative_to(ROOT)) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md'))
    save(output/'sources.json',{p:digest(ROOT/p) for p in sorted(paths)})
    omitted=[];members=[];seen={}
    with tarfile.open(output/'development.tar.gz','w:gz') as tar:
        for p in sorted(development.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts:continue
            rel=p.relative_to(development).as_posix()
            if run in p.parents:continue
            # Original refusals, commands and source snapshots are retained.
            # Complete, superseded success payloads are recorded by identity.
            failed=any((parent/'failure.txt').exists() for parent in p.parents if development==parent or development in parent.parents)
            if not failed and p.suffix=='.gz' and p.name in ('functions.json.gz','calls.json.gz','samples.json.gz','delta.json.gz'):
                omitted.append(dict(path=rel,sha256=digest(p),status='SUPERSEDED_SUCCESS_HASH_ONLY'));continue
            raw=p.read_bytes();sha=digest(p);info=tarfile.TarInfo(rel);info.mode=0o644;info.mtime=0
            if sha in seen:info.type=tarfile.LNKTYPE;info.linkname=seen[sha];tar.addfile(info)
            else:info.size=len(raw);tar.addfile(info,io.BytesIO(raw));seen[sha]=rel
            members.append(dict(path=rel,sha256=sha,bytes=len(raw)))
    save(output/'development-members.json',members);save(output/'superseded-successes.json',omitted)
    save(output/'packet.json',dict(version=1,id='NATIVE-BUILD-FLOW-R1',review_disposition='NOT_REVIEWED',
        timestamp=datetime.now(timezone.utc).isoformat(),scope=summary,
        implementation_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p))for p in sorted(output.iterdir())if p.is_file()]))
    print('Retained',len(list(output.iterdir())),'files;',sum(p.stat().st_size for p in output.iterdir()),'bytes.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','development','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();finalize(a.run.resolve(),a.development.resolve(),a.output.resolve())
