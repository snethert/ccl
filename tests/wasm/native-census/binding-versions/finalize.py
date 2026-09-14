"""Publish one small diagnostic packet with original development failures."""
import argparse
from datetime import datetime,timezone
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
from common import HERE,ROOT,read,save,digest,require
from verify import OUTPUTS


def finalize(run,development,output):
    output.mkdir(parents=True,exist_ok=False)
    summary=read(run/'summary.json')
    require(summary['integration']['structural_contract']=='PASS' and summary['census_gate_credit'] is False,'RUN_COMPLETION')
    pins=read(run/'run.json')['source_sha256']
    for path,sha in pins.items():require(digest(ROOT/path)==sha,'EXECUTED_SOURCE '+path)
    for name in OUTPUTS+('run.json',):shutil.copyfile(run/name,output/name)
    for name in ('inputs.json','development.md'):shutil.copyfile(HERE/name,output/name)
    paths=set(pins)|{str(p.relative_to(ROOT)) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md')}
    save(output/'sources.json',{p:digest(ROOT/p) for p in sorted(paths)})
    members=[];seen={}
    with tarfile.open(output/'development.tar.gz','w:gz') as tar:
        for p in sorted(development.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or run in p.parents:continue
            rel=p.relative_to(development).as_posix();raw=p.read_bytes();sha=digest(p)
            info=tarfile.TarInfo(rel);info.mode=0o644;info.mtime=0
            if sha in seen:info.type=tarfile.LNKTYPE;info.linkname=seen[sha];tar.addfile(info)
            else:info.size=len(raw);tar.addfile(info,io.BytesIO(raw));seen[sha]=rel
            members.append(dict(path=rel,bytes=len(raw),sha256=sha))
    save(output/'development-members.json',members)
    save(output/'packet.json',dict(version=1,id='NATIVE-BINDING-VERSIONS-R1',review_disposition='NOT_REVIEWED',
        timestamp=datetime.now(timezone.utc).isoformat(),scope=summary,
        implementation_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(output.iterdir()) if p.is_file()]))
    print('Retained',len(list(output.iterdir())),'files;',sum(p.stat().st_size for p in output.iterdir()),'bytes.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','development','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();finalize(a.run.resolve(),a.development.resolve(),a.output.resolve())
