#!/usr/bin/env python3
"""Explicit build, probe, execution and verification entry points."""
import argparse
from pathlib import Path
import json
import common as c


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cache',type=Path,default=c.DEFAULT_CACHE)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('build');p.add_argument('output',type=Path);p.add_argument('--cold',action='store_true');p.add_argument('--jobs',type=int,default=4)
    p=commands.add_parser('probe');p.add_argument('base',type=Path);p.add_argument('source',type=Path);p.add_argument('inputs',type=Path);p.add_argument('output',type=Path);p.add_argument('--mode',choices=['class','default'],default='default');p.add_argument('--jobs',type=int,default=4);p.add_argument('--workers',type=int,default=4)
    p=commands.add_parser('verify');p.add_argument('output',type=Path);p.add_argument('--tier',choices=['identity','focused','full'],required=True);p.add_argument('--parent',type=Path);p.add_argument('--workers',type=int,default=4);p.add_argument('--indices',type=Path);p.add_argument('--reverse',action='store_true')
    args=parser.parse_args()
    # The fixed proposal also binds its disposable-U1 installer. A different
    # installer requires a newly qualified parent, never a cache hit.
    unit='tests/wasm/stage1/registration/unit.py'
    c.verify_files(c.ROOT,{unit:c.read(c.PARENT/'source-pins.json')[unit]})
    dependencies=c.read(c.PARENT/'dependencies.json')
    inputs=(c.KERNEL,c.IMAGE,c.STORE/'macos-u1-inputs/source.tar',c.STORE/'macos-u1-inputs/bootstrap.tar.gz')
    c.verify_files(c.STORE,{str(p.relative_to(c.STORE)):dependencies[str(p.relative_to(c.STORE))] for p in inputs})
    for field in ('workers','jobs'):
        if hasattr(args,field) and not 1<=getattr(args,field)<=16:parser.error(field+' must be between 1 and 16')
    if args.command=='build':
        from build import build
        result=build(args.output.resolve(),args.cache.resolve(),args.jobs,args.cold)
    elif args.command=='probe':
        from probe import probe
        from execute import execute
        result=probe(args.base,args.source,args.inputs,args.output,args.cache,args.mode,args.jobs)
        result['execution']=execute(args.output,args.workers,indices=result['indices'])
        c.save(args.output/'probe-completion.json',result)
    elif args.tier=='identity':
        from execute import identity
        result=identity(args.output)
    else:
        from execute import execute
        indices=c.read(args.indices) if args.indices else None
        result=execute(args.output,args.workers,args.tier,args.parent,indices,args.reverse)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
