#!/usr/bin/env python3
"""Verify compacted evidence or recover its sources/results/failing inputs."""
from pathlib import Path, PurePosixPath
import argparse
import gzip
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]


def location(pack,row):
    if 'retained' in row:
        path=(pack/row['retained']).resolve()
        if not path.is_relative_to(pack.resolve()):raise ValueError('escaping retained path')
        return path
    if 'shared_input' in row:
        path=(pack.parent/row['shared_input']).resolve()
        if not path.is_relative_to((pack.parent/'shared-inputs').resolve()):raise ValueError('escaping shared input')
        return path
    return None


def verify(pack):
    manifest=json.loads((pack/'compaction.json').read_text());checked={}
    for artifact in manifest['original_files'].values():
        for row in artifact.get('members',{}).values():
            path=location(pack,row)
            if path is None:continue
            identity=(row['sha256'],row.get('stored_sha256'),row.get('encoding'))
            if path in checked:
                if checked[path]!=identity:raise ValueError('conflicting retained identities')
                continue
            if row.get('stored_sha256'):
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=row['stored_sha256']:
                        raise ValueError('stored bytes changed: '+str(path))
            opener=gzip.open if row.get('encoding')=='gzip' else open
            with opener(path,'rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:
                    raise ValueError('original bytes changed: '+str(path))
            checked[path]=identity
    return dict(status='PASS',retained_files=len(checked),
                scope='Retained original bytes; elided compiled products were not rebuilt')


def extract(pack,archive,out):
    sys.path.insert(0,str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
    import storage
    manifest=json.loads((pack/'compaction.json').read_text())
    members=manifest['original_files'][archive]['members']
    skipped={}
    with storage.lease([out]):
        if out.exists():raise ValueError('output already exists')
        out.mkdir(parents=True)
        for name,row in members.items():
            relative=PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('escaping archive member')
            source=location(pack,row)
            if source is None:skipped[name]=row;continue
            target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
            opener=gzip.open if row.get('encoding')=='gzip' else open
            with opener(source,'rb') as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
            with target.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:
                    raise ValueError('original member identity: '+name)
        (out/'elided-products.json').write_text(json.dumps(skipped,indent=2)+'\n')
    return dict(status='PASS',restored=len(members)-len(skipped),elided=len(skipped),
                scope='Review inputs; rebuild pinned sources to execute')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pack',type=Path)
    p.add_argument('--extract',metavar='ORIGINAL_ARCHIVE');p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.extract and not a.output:p.error('--extract requires --output')
    print(json.dumps(extract(a.pack.resolve(),a.extract,a.output.resolve()) if a.extract else verify(a.pack.resolve())))
