#!/usr/bin/env python3
"""Index registry writes and their value dependencies from the original build IR."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'finite-callees'))
from lexical_run import read,save,convert,require
from lexical import Resolver,Unbounded

STORES={'CCL::STRUCT-SET','CCL::%SVSET','CCL::SVSET','CCL::UVSET',
        'COMMON-LISP::RPLACA','COMMON-LISP::RPLACD','CCL::%RPLACA','CCL::%RPLACD'}


def expression(g,value,seen=()):
    """A lossless reference to unfamiliar values; only familiar syntax expands."""
    n=g.node(value)
    if not n:return value
    if n['id'] in seen:return dict(cycle=n['id'])
    if len(seen)>40:return dict(reference=n['id'],kind=n['kind'])
    seen=seen+(n['id'],)
    if n['kind']=='variable':return dict(variable=n['root'],name=n['name'])
    if n['kind']=='function':return dict(function=n['id'],name=n['name'])
    if n['kind']=='acode':return dict(node=n['id'],operator=n['operator'],
        arguments=[expression(g,x,seen) for x in g.items(n['operands'])])
    if n['kind']=='cons':return dict(node=n['id'],car=expression(g,n['car'],seen),cdr=expression(g,n['cdr'],seen))
    return n


def receiver_type(g,value):
    n=g.node(value)
    if n and n.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
        args=g.items(n['operands'])
        if isinstance(args[0],dict) and 'identity' in args[0]:return args[0]
    return None


def scan(cache,store,out):
    out.mkdir(parents=True,exist_ok=False)
    functions=read(store/'2026-09-14-build-flow-r1/functions.json.gz')
    by_event={}
    for f in functions:by_event.setdefault(f['event'],{})[f['function_id']]=f
    samples=read(store/'2026-09-14-build-flow-r1/samples.json.gz')
    ops={int(k):v for k,v in next(iter(samples.values()))['operators'].items()}
    selected={event for event,fns in by_event.items()
              if any(ops[o['id']] in STORES for f in fns.values() for o in f['operators'])}
    rows=[];seen=set();counts=Counter()
    with gzip.open(cache,'rt') as src,gzip.open(out/'writer-ir.jsonl.gz','wb',compresslevel=1) as retained:
        for line in src:
            row=json.loads(line);seq=row['sequence']
            if seq not in selected:continue
            require(seq not in seen,'DUPLICATE_WRITER_EVENT');seen.add(seq)
            r=Resolver(convert(row['payload'],ops));g=r.graph
            require(set(r.family)==set(by_event[seq]),'WRITER_FUNCTION_JOIN')
            symbols={n['id']:n for n in row['payload']['ir']['objects'] if n['kind']=='symbol'}
            for owner,fn in r.family.items():
                for n in g.body(owner):
                    if n['operator'] not in STORES:continue
                    args=g.items(n['operands']);counts[n['operator']]+=1
                    count=2 if n['operator'].endswith(('RPLACA','RPLACD')) else 3
                    require(len(args)==count,'WRITER_OPERANDS')
                    index=g.node(args[1]) if count==3 else None
                    slot=(g.items(index['operands'])[0] if index and index.get('operator')=='COMMON-LISP::FIXNUM' else None)
                    result=dict(function_id=owner,site_id=n['id'],name=fn['name'],event=seq,source=row['source'],
                                source_position=row['source_position'],operator=n['operator'],
                                receiver_type=receiver_type(g,args[0]),slot=slot,
                                receiver=expression(g,args[0]),value=expression(g,args[-1]))
                    try:
                        candidates,steps=r.resolve(args[-1],owner,n['id'])
                        targets=[dict(kind=k,id=i,mode=m) for k,i,m in sorted(candidates)]
                        for t in targets:
                            if t['kind']=='symbol':t['descriptor']=symbols[t['id']]
                        result.update(status='FINITE_VALUE',targets=targets,steps=steps)
                    except Unbounded as e:result.update(status='UNRESOLVED_VALUE',targets=[],reason=str(e))
                    rows.append(result)
            retained.write(line.encode())
            if len(seen)%500==0:print('Indexed',len(seen),'writer families.',flush=True)
    require(seen==selected,'WRITER_EVENT_COVERAGE')
    rows.sort(key=lambda r:(r['function_id'],r['site_id']))
    require(len({(r['function_id'],r['site_id']) for r in rows})==len(rows),'DUPLICATE_WRITE')
    save(out/'writes.json.gz',rows)
    summary=dict(writer_families=len(seen),writes=len(rows),operators=dict(counts),
                 finite_values=sum(r['status']=='FINITE_VALUE' for r in rows),
                 scope='Original build IR writes only; constructor defaults, aliasing, incoming arguments and unobserved bodies still require joins.')
    save(out/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    scan(a.cache,a.evidence,a.output)
