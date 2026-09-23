"""One full sequential-corpus comparison, then focused ordering checks."""
from pathlib import Path
import argparse
import copy
import shutil
import tarfile
import common as c
from execute import execute, bound_report, sample


def clone(base,out):
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('compiler.image','*.log','execution-report*','parallel-results.json'))


def retained(out):
    expected=c.read(c.PARENT/'deterministic.json')
    with tarfile.open(c.PARENT/'execution.tar.gz') as archive:
        for name in ('compiled/native.json','execution.json'):
            path=out/name
            path.write_bytes(archive.extractfile(name).read())
            if c.sha(path)!=expected[name]:raise ValueError('retained sequential artifact')


def compare_sequential(out):
    rows=c.read(out/'compiled/native.json');ids=c.read(out/'case-ids.json')
    callers=set(c.read(out/'compiled/condition-callers.json'))
    order=sorted(range(len(rows)),key=lambda i:rows[i]['definition'] not in callers)
    expected={}
    for placement in c.read(out/'execution.json')['rows']:
        old=placement['rows'];assert len(old)==len(order)*2
        for index,i in enumerate(order):
            for move in (False,True):
                row=old[2*index+int(move)]
                assert row['name']==rows[i]['name'] and row['moved']==move
                expected[(ids[i],placement['base'],move)]=row
    report,_=bound_report(out/'execution-report.json')
    for case in report['cases']:
        for row in case['results']:
            before=expected[(case['id'],row['base'],row['moved'])]
            after={k:v for k,v in row.items() if k not in ('base','caseId')}
            if before!=after:raise ValueError('parallel/sequential mismatch: '+case['id'])
    result=dict(status='PASS',comparisons=len(expected),values=True,mutations=True,
                conditions=True,thread_restoration='asserted by every invocation',
                sequential_sha256=c.sha(out/'execution.json'))
    c.save(out/'sequential-comparison.json',result)
    return result


def qualify(base,out,workers=4):
    out=Path(out);out.mkdir()
    baseline=out/'retained';clone(base,baseline);retained(baseline)
    execute(baseline,workers)
    comparison=compare_sequential(baseline)
    # The checkpoint's fresh native oracle can change the identity graph of
    # host class caches. It is an input change, never an excuse to inherit it.
    delta=out/'fresh-oracle';clone(base,delta)
    forward=execute(delta,workers,'focused',baseline/'execution-report.json')
    sequential=out/'focused-sequential';clone(base,sequential)
    reverse=execute(sequential,1,'focused',baseline/'execution-report.json',reverse=True)
    a,_=bound_report(delta/'execution-report.json');b,_=bound_report(sequential/'execution-report.json')
    assert [(x['id'],x['results']) for x in a['cases']]==[(x['id'],x['results']) for x in b['cases']]
    # Explicitly revisit stateful cases even if they were not chosen by the
    # fixed regression sample in a future parent corpus.
    native=c.read(base/'compiled/native.json')
    chosen=[i for i,r in enumerate(native) if r['definition'] in
        ('CORE-CONDITION-TABLE-GROW','CORE-CONDITION-IMPLICIT-DIVIDE','CORE-SPECIAL-SETQ')]
    globals_=[i for i,r in enumerate(native) if r.get('globals')]
    chosen=sorted(set(chosen+globals_[:8]))
    assert globals_ and any(native[i]['definition']=='CORE-CONDITION-TABLE-GROW' for i in chosen)
    state=out/'stateful';clone(base,state)
    execute(state,1,indices=chosen)
    old=out/'stateful-before.json';shutil.copyfile(state/'execution-report.json',old)
    shutil.copyfile(state/'execution-report.identity.json',old.with_suffix('.identity.json'))
    execute(state,workers,indices=list(reversed(chosen)))
    before,_=bound_report(old);after,_=bound_report(state/'execution-report.json')
    assert {r['id']:r['results'] for r in before['cases']}=={r['id']:r['results'] for r in after['cases']}
    result=dict(status='PASS',sequential_comparison=comparison,focused_parallel=forward,
                focused_sequential=reverse,stateful_cases=len(chosen),workers=workers)
    c.save(out/'qualification.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(qualify(a.base,a.output))
