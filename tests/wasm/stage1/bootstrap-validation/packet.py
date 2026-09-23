"""Retain completed evidence; restore review inputs without compiling the corpus."""
from pathlib import Path
import argparse
import shutil
import tarfile
import common as c
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
    out.mkdir()
    pack(entry,out/'session.tar.gz',c.inventory(entry).keys()|{'cache-manifest.json'})
    session_files=c.read(entry/'cache-manifest.json')['files']
    changed={n:h for n,h in c.inventory(report).items() if session_files.get(n)!=h}
    pack(report,out/'review.tar.gz',changed)
    c.save(out/'review-files.json',changed)
    evidence={str(p.relative_to(qualification)):c.sha(p) for p in c.files(qualification)
              if p.suffix in ('.json','.log') and not any(part in ('compiled','driver','runtime','owner-check') for part in p.relative_to(qualification).parts)}
    pack(qualification,out/'qualification.tar.gz',evidence)
    c.save(out/'qualification-files.json',evidence)
    probe_files={n:h for n,h in c.inventory(probe).items() if session_files.get(n)!=h}
    probe_files.pop('compiled/compiler.image',None)
    pack(probe,out/'probe.tar.gz',probe_files)
    c.save(out/'probe-files.json',probe_files)
    for name,path in [('qualification.json',qualification/'qualification.json'),('controls.json',controls/'controls.json'),
                      ('probe-controls.json',controls/'probe-controls.json'),('warm.json',warm/'build-invocation.json'),('build.json',base/'build-invocation.json'),
                      ('probe.json',probe/'probe-completion.json')]:shutil.copyfile(path,out/name)
    pack(controls,out/'controls.tar.gz',c.inventory(controls))
    shutil.copytree(c.HERE,out/'source',ignore=shutil.ignore_patterns('__pycache__'))
    if development:
        pack(Path(development),out/'development.tar.gz',c.inventory(Path(development)))
    c.save(out/'provenance.json',dict(parent=str(c.PARENT.name),parent_packet=c.sha(c.PARENT/'packet.json'),
        native_qualification=dict(status='REUSED',parent_summary=c.sha(c.PARENT/'summary.json'),
            qualified_proposal=c.inventory(entry/'compiled/proposal'),native_tests=21843,
            source_change=False,execution_rebuilt=False),
        compiler_session_key=key,compiler_image=c.sha(entry/'compiled/compiler.image'),
        author_execution=c.sha(original/'execution-report.json'),execution_rebuilt_during_retention=False,
        admission_credit=0,original_definition_execution_credit=0,slot_credit=False))
    c.save(out/'packet.json',dict(id='STAGE1-BOOTSTRAP-VALIDATION-R1',review_disposition='NOT_REVIEWED',
        slot_credit=False,files=c.inventory(out),tool_sources=c.inventory(c.HERE)))
    return dict(status='PASS',packet=str(out),execution_rebuilt=False)


def restore(packet,out,cache):
    packet,out,cache=map(Path,(packet,out,cache));manifest=checked(packet)
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
    if a.command=='restore':print(restore(a.packet,a.output,a.cache))
    else:print(retain(a.base,a.qualification,a.probe,a.controls,a.warm,a.cache,a.output,a.development))
