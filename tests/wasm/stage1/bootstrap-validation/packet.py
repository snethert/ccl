"""Retain completed evidence; restore review inputs without compiling the corpus."""
from pathlib import Path
import argparse
import shutil
import tarfile
import common as c
import storage
from execute import identity,bound_report


def pack(root,dest,names):
    with tarfile.open(dest,'w:gz',compresslevel=1) as archive:
        for name in sorted(names):archive.add(root/name,arcname=name,recursive=False)


def checked(packet):
    manifest=c.read(packet/'packet.json')
    c.verify_files(packet,manifest['files'])
    actual=set(c.inventory(packet))-{'packet.json'}
    if actual!=set(manifest['files']):raise ValueError('packet inventory')
    c.verify_files(c.HERE,manifest['tool_sources'])
    return manifest


def retain(base,qualification,probe,controls,warm,cache,out,development):
    base,qualification,probe,controls,warm,cache,out=map(Path,(base,qualification,probe,controls,warm,cache,out))
    disposable=[base,qualification,probe,controls,warm]
    for path in disposable:
        storage.workspace(path)
        if path.resolve()==out.resolve() or path.resolve() in out.resolve().parents:
            raise ValueError('packet must be outside disposable input trees')
    assert c.read(qualification/'qualification.json')['status']=='PASS'
    assert c.read(controls/'controls.json')['status']=='PASS'
    assert c.read(controls/'probe-controls.json')['status']=='PASS'
    probe_record=c.read(probe/'probe-completion.json');assert probe_record['execution']['status']=='PASS'
    warm_record=c.read(warm/'build-invocation.json')
    assert warm_record['compiler_processes']==warm_record['oracle_processes']==warm_record['wabt_processes']==0
    report=qualification/'fresh-oracle';identity(report)
    original=qualification/'retained';identity(original)
    key=c.read(base/'build-invocation.json')['key'];entry=c.cache_read(cache,'session',key)
    if entry is None:raise ValueError('missing retained session')
    import artifacts
    import tempfile
    import os
    if out.exists(): raise ValueError('retained destination exists')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.retaining-',dir=out.parent) as temporary:
        stage=Path(temporary)/'packet';stage.mkdir()
        for label,path in [('build',base),('qualification',qualification),('probe',probe),('controls',controls),('warm',warm)]:
            artifacts.snapshot(path,stage/label,oracle_store=c.STORE/'shared-inputs/oracles')
        if development:
            c.save(stage/'experiments.json',dict(files=c.inventory(development)))
            failures=artifacts.explicit_failures(Path(development))
            for name in failures:
                target=stage/'failure-inputs'/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(Path(development)/name,target)
            for path in c.files(development):
                if path.suffix in ('.json','.log') and not artifacts.product(path.name):
                    target=stage/'experiment-results'/path.relative_to(development)
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        shutil.copytree(c.HERE,stage/'source',ignore=shutil.ignore_patterns('__pycache__'))
        c.save(stage/'provenance.json',dict(parent=str(c.PARENT.name),
            compiler_session_key=key,compiler_image=c.sha(entry/'compiled/compiler.image'),
            execution_rebuilt_during_retention=False,review_only=True))
        c.save(stage/'packet.json',dict(version=3,id='BOOTSTRAP-VALIDATION-RESULTS',
            review_disposition='NOT_REVIEWED',files=c.inventory(stage),tool_sources=c.inventory(c.HERE)))
        artifacts.check_size(stage)
        checked(stage)
        os.rename(stage,out)
    # Delete only after the complete destination has passed identity validation.
    for path in sorted(set(disposable),key=lambda p:len(p.parts),reverse=True):
        if path.exists():shutil.rmtree(path)
    return dict(status='PASS',packet=str(out),execution_rebuilt=False)


def restore(packet,out,cache):
    packet,out,cache=map(Path,(packet,out,cache))
    if (packet/'compaction.json').exists():
        raise ValueError('Compiled artifacts were compacted. Use doc/WASM/tools/read-compacted-evidence.py for review inputs, or rebuild the pinned source to execute.')
    manifest=checked(packet)
    if manifest.get('version')==3:
        raise ValueError('This is review evidence. Rebuild the pinned compiler to execute; compiled artifacts are not retained.')
    key=c.read(packet/'provenance.json')['compiler_session_key']
    entry=c.cache_read(cache,'session',key)
    if entry is None:
        with c.cache_write(cache,'session',key) as stage:
            c.extract(packet/'session.tar.gz',stage)
            inner=c.read(stage/'cache-manifest.json')
            if inner['key']!=key or inner['kind']!='session':raise ValueError('retained cache identity')
            c.verify_files(stage,inner['files'])
        entry=c.cache_read(cache,'session',key)
    out.mkdir();shutil.copytree(entry,out,dirs_exist_ok=True);(out/'cache-manifest.json').unlink()
    c.extract(packet/'review.tar.gz',out);c.verify_files(out,c.read(packet/'review-files.json'))
    # Seed individually bound WABT entries from retained WAT/binary pairs.
    for row in c.read(out/'assembly.json')['rows']:
        path=out/'compiled'/row['name'];binding=c.assembly_key(path)
        if c.digest(binding)!=row['key']:raise ValueError('retained assembly identity')
        if c.cache_read(cache,'wabt',row['key']) is None:
            with c.cache_write(cache,'wabt',row['key']) as stage:
                shutil.copyfile(path.with_suffix('.wasm'),stage/'module.wasm')
                c.save(stage/'identity.json',binding)
                (stage/'wabt.log').write_text('Restored from '+c.sha(packet/'packet.json')+'\n')
    result=identity(out);result['restored_session']=key;return result


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('retain')
    for name in ('base','qualification','probe','controls','warm','cache','output'):q.add_argument(name,type=Path)
    q.add_argument('--development',type=Path)
    q=sub.add_parser('restore');q.add_argument('packet',type=Path);q.add_argument('output',type=Path);q.add_argument('--cache',type=Path,default=c.DEFAULT_CACHE)
    a=p.parse_args()
    paths=[a.output] if a.command=='restore' else [a.base,a.qualification,a.probe,a.controls,a.warm]
    for path in paths:storage.workspace(path)
    storage.gc(a.cache)
    try:
        with storage.lease(paths,a.cache):
            if a.command=='restore':print(restore(a.packet,a.output,a.cache))
            else:print(retain(a.base,a.qualification,a.probe,a.controls,a.warm,a.cache,a.output,a.development))
    finally:storage.gc(a.cache)
