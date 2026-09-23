#!/usr/bin/env python3
"""Retain class-image evidence without copying the existing compiler session."""
from pathlib import Path
import argparse
import json
import shutil
import sys
import tarfile
import subprocess
from run import HERE,summary,run,c,storage


def pack(root,destination,names):
    with tarfile.open(destination,'w:gz',compresslevel=6) as stream:
        for name in sorted(names):stream.add(root/name,arcname=name,recursive=False)


def retain(output,packet):
    storage.workspace(output)
    if output.resolve()==packet.resolve() or output.resolve() in packet.resolve().parents:
        raise ValueError('retained packet overlaps disposable output')
    result=summary(output);packet.mkdir()
    for name in ('summary.json','writer.json','reader.json','boot.json','controls.json'):
        shutil.copyfile(output/name,packet/name)
    for name in ('execution-report.json','execution-report.identity.json','build-invocation.json',
                 'class-image-code.json','class-image-code.sha256'):
        shutil.copyfile(output/'base'/name,packet/name)
    # The unchanged baseline worker never imports this new module. Its full
    # report nevertheless inventories runtime files present beside it. Retain
    # the exact earlier bytes for that record, rather than relabelling the run.
    baseline=c.read(output/'base/execution-report.json')['environment']['files']
    if 'runtime/heap-image.mjs' in baseline:
        old=(output/'base/runtime/heap-image.mjs').read_text()
        old=old.replace('const RELOCATION=0xfffffff9; // remains a pointer until its required patch is applied\n','')
        old=old.replace('v.setUint32(slot,RELOCATION,true)','v.setUint32(slot,0,true)')
        old=old.replace('view.getUint32(x.slot,true)===RELOCATION','view.getUint32(x.slot,true)===0')
        import hashlib
        assert hashlib.sha256(old.encode()).hexdigest()==baseline['runtime/heap-image.mjs']
        (packet/'baseline-unused-heap-image.mjs').write_text(old)
    images=c.inventory(output/'images');c.save(packet/'images.json',images)
    pack(output/'images',packet/'images.tar.gz',images)
    logs=[p.name for p in output.glob('*.log')]
    pack(output,packet/'development-logs.tar.gz',logs)
    shutil.copytree(HERE,packet/'source',ignore=shutil.ignore_patterns('__pycache__'))
    sources={str(p.relative_to(c.ROOT)):c.sha(p) for p in c.files(HERE)}
    for path in c.files(HERE.parent/'bootstrap-validation'):
        sources[str(path.relative_to(c.ROOT))]=c.sha(path)
    sources.update({'runtime/wasm32/sha256.mjs':c.sha(c.ROOT/'runtime/wasm32/sha256.mjs')})
    c.save(packet/'source-pins.json',sources)
    c.save(packet/'provenance.json',dict(
        parent=c.PARENT.name,parent_packet=c.sha(c.PARENT/'packet.json'),
        session=c.read(output/'base/build-invocation.json')['key'],
        proposal_sources=c.inventory(output/'base/compiled/proposal'),
        native_qualification='Reused by unchanged proposal source identity; no compiler/CCL source edits.',
        author_full_execution=c.sha(output/'base/execution-report.json'),
        source_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
        execution_during_retention=False,original_definition_credit=0,slot_credit=False))
    c.save(packet/'packet.json',dict(id='STAGE1-CLASS-IMAGE-R1',review_disposition='NOT_REVIEWED',
                                  files=c.inventory(packet),slot_credit=False))
    c.verify_files(packet,c.read(packet/'packet.json')['files'])
    shutil.rmtree(output)
    return dict(status='PASS',packet=str(packet),summary=result)


def verify(packet,output):
    manifest=c.read(packet/'packet.json');c.verify_files(packet,manifest['files'])
    if set(c.inventory(packet))-{'packet.json'}!=set(manifest['files']):raise ValueError('packet file set')
    c.verify_files(c.ROOT,c.read(packet/'source-pins.json'))
    actual=run(output)
    assert actual==c.read(packet/'summary.json')
    assert c.inventory(output/'images')==c.read(packet/'images.json')
    for name in ('writer.json','reader.json','boot.json','controls.json'):
        assert c.sha(output/name)==c.sha(packet/name),name
    return dict(status='PASS',execution_rebuilt=True,summary=actual)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['retain','verify'])
    parser.add_argument('packet',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with storage.lease([args.output]):
        print(json.dumps(retain(args.output,args.packet) if args.command=='retain' else verify(args.packet,args.output),sort_keys=True))
