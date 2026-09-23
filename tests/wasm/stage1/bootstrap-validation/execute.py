"""Provenance-aware execution and deterministic parallel result merging."""
from pathlib import Path
import json
import shutil
import time
import common as c
from prepare import prepare

SEED=0x42545034


def row_key(environment,row,case_id):
    return c.digest(dict(environment=environment,case=case_id,oracle=row))


def sample(ids,count=32):
    return sorted(ids,key=lambda x:c.digest([SEED,x]))[:count]


def bound_report(path):
    path=Path(path)
    value=c.read(path)
    identity=c.read(path.with_suffix('.identity.json'))
    if c.sha(path)!=identity['sha256']:
        raise ValueError('execution report identity: '+str(path))
    if value['status']!='PASS':raise ValueError('unsuccessful parent execution')
    if c.digest(value['environment'])!=value['environment_key'] or identity['environment']!=value['environment_key']:
        raise ValueError('execution environment identity')
    return value,identity


def execute(out,workers=4,tier='full',parent=None,indices=None,reverse=False,controls=True):
    out=Path(out);start=time.monotonic();prepare(out)
    env=c.read(out/'execution-environment.json');env_key=c.digest(env)
    rows=c.read(out/'compiled/native.json');ids=c.read(out/'case-ids.json')
    keys=[row_key(env_key,row,case_id) for row,case_id in zip(rows,ids)]
    old={};parent_id=None
    if parent and Path(parent).exists() and Path(parent).with_suffix('.identity.json').exists():
        previous,parent_id=bound_report(parent)
        parent_id={**parent_id,'report':str(Path(parent).resolve())}
        old={r['key']:r for r in previous['cases']}
    wanted=list(range(len(rows))) if indices is None else list(indices)
    if len(set(wanted))!=len(wanted) or any(not 0<=i<len(rows) for i in wanted):raise ValueError('case selection')
    unchanged=[i for i in wanted if keys[i] in old]
    changed=[i for i in wanted if keys[i] not in old]
    sampled=[]
    if tier=='full':selected=wanted
    elif tier=='focused':
        sampled_ids=set(sample([ids[i] for i in unchanged]));sampled=[i for i in unchanged if ids[i] in sampled_ids]
        selected=changed+sampled
    else:raise ValueError('execution tier')
    if reverse:selected.reverse()
    control_indices=[]
    if controls:
        control_indices=[next(i for i,r in enumerate(rows) if r['definition']=='CORE-CONDITION-TABLE-GROW' and r['values'][1]==1500),
                         next(i for i,r in enumerate(rows) if r['definition']=='CORE-GENERIC-READER-DISPATCH')]
    plan=dict(workers=workers,indices=selected,controls=controls,controlIndices=control_indices)
    c.save(out/'execution-plan.json',plan)
    seconds=c.command([c.NODE,out/'parallel.mjs',out,out/'execution-plan.json',out/'parallel-results.json'],out/'execution.log',timeout=1200)
    fresh=c.read(out/'parallel-results.json');by_id={}
    for row in fresh['rows']:by_id.setdefault(row['caseId'],[]).append(row)
    cases=[]
    for i in wanted:
        key=keys[i]
        if ids[i] in by_id:
            results=by_id[ids[i]]
            if len(results)!=4:raise ValueError('incomplete case execution')
            if key in old and results!=old[key]['results']:raise ValueError('reused case disagrees: '+ids[i])
            cases.append(dict(id=ids[i],key=key,results=results,origin='sampled' if i in sampled else 'fresh'))
        else:
            row=old[key]
            cases.append(dict(id=ids[i],key=key,results=row['results'],origin='inherited',parent=parent_id))
    extra={}
    if controls:
        for program,output,args in (
            ('istruct-check.mjs','istruct-checks.json',[out/'collector.wasm']),
            ('population-check.mjs','population-checks.json',[out/'collector.wasm']),
            ('owner-check/check.mjs','owner-check/results.json',[out/'collector.wasm'])):
            c.command([c.NODE,out/program,*args,out/output],out/(Path(program).stem+'.log'))
            extra[output]=c.read(out/output)
        assert extra['owner-check/results.json']['checks']==40
    report=dict(status='PASS',version=1,tier=tier,execution_rebuilt=bool(selected or controls),environment=env,
        environment_key=env_key,seed=SEED,workers=workers,cases=cases,
        fresh_comparisons=4*(len(selected)-len(sampled)),sampled_comparisons=4*len(sampled),
        inherited_comparisons=4*(len(wanted)-len(selected)),control_results=fresh['controls'],
        extra_controls=extra,collections=fresh['collections'],execution_seconds=seconds,total_seconds=time.monotonic()-start)
    path=out/'execution-report.json';c.save(path,report)
    c.save(path.with_suffix('.identity.json'),dict(sha256=c.sha(path),environment=env_key,
           parent=parent_id,status='PASS',native=c.sha(out/'compiled/native.json'),ids=c.sha(out/'case-ids.json')))
    return {k:report[k] for k in ('status','tier','fresh_comparisons','sampled_comparisons','inherited_comparisons','execution_seconds')}


def identity(out):
    out=Path(out)
    report,binding=bound_report(out/'execution-report.json')
    c.verify_files(out,report['environment']['files'])
    if c.sha(c.NODE)!=report['environment']['engine']['sha256']:
        raise ValueError('engine identity')
    if c.sha(out/'compiled/native.json')!=binding['native'] or c.sha(out/'case-ids.json')!=binding['ids']:
        raise ValueError('execution inputs changed')
    for name,expected in report['environment']['tooling'].items():
        if c.sha(c.HERE/name)!=expected:raise ValueError('execution tooling changed: '+name)
    return dict(status='PASS',tier='identity',execution_rebuilt=False,
                comparisons_executed=0,validated_report=binding)
