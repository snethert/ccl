"""Attach the remaining source bodies reached by resident dispatch literals."""
from copy import deepcopy
from pathlib import Path
import hashlib
from payloads import read,save,require,capture,correspondences
from nested_bodies import closure,materialized_candidates,pairs,qualify
from deferred import index as deferred_index
from bodies import extract,with_initializers,needed_matches,make,apply

HERE=Path(__file__).resolve().parent


def check(base,graph,delta,matches,families,calls,support,deferred):
    expected=make(base,matches,families,calls,support,deferred,
        namespace='dispatch-bodies:',anchor_evidence='resident-literals/body/')
    require(delta==expected,'DISPATCH_BODY_DELTA')
    require(graph==apply(base,expected),'DISPATCH_BODY_GRAPH')


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    base=read(a.base)
    requested={int(e['evidence'].split('/')[-1]) for e in read(a.requests)['edges']
        if e['evidence'].startswith('resident-literals/body/')}
    require(requested,'DISPATCH_NO_REQUESTS')
    fs,em,_,wr,_=capture(a.capture/'registries.jsonl.gz')
    idx=read(a.previous/'compiler-index.json.gz')
    before={int(k):v for k,v in idx['before'].items()};late={int(k):v for k,v in idx['late_notes'].items()}
    loader={int(k):v for k,v in read(a.previous/'loader-body-joins.json.gz')['joins'].items()}
    asks=dict(bodies=[dict(code=i,payload_sha256=hashlib.sha256(bytes.fromhex(fs[i]['payload_hex'])).hexdigest())
        for i in sorted(closure(fs,requested))])
    deferred=read(a.bodies/'deferred-initializers.json.gz')
    candidates,missing=correspondences(fs,materialized_candidates(fs,em,loader),wr,asks,before,late,
        read(a.previous/'source-coordinate-map.json'),data_dependencies=True,candidate_function_literals=True,
        deferred=deferred_index(deferred))
    relation,_=pairs(fs,candidates);qualified=qualify(fs,candidates,relation)
    matches=[m for m in qualified if m['bootstrap_code'] in requested]
    support=[m for m in qualified if m['bootstrap_code'] not in requested]
    require({m['bootstrap_code'] for m in matches}==requested,'DISPATCH_BODY_COVERAGE')
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    families,calls=extract(a.capture/'build.jsonl.gz',with_initializers(needed_matches(matches,support),deferred['placeholders']),ops)
    delta=make(base,matches,families,calls,support,deferred['placeholders'],namespace='dispatch-bodies:',
               anchor_evidence='resident-literals/body/')
    graph=apply(base,delta)
    check(base,graph,delta,matches,families,calls,support,deferred['placeholders'])
    tests=[]
    for name,mutate in [
        ('omit-body',lambda d:d['replacements'].pop()),
        ('substitute-body',lambda d:d['replacements'][0].update(targets=['dispatch-bodies:qualification'])),
        ('invent-call',lambda d:d['edges'].append(d['edges'][0])),
        ('promote-target-lowering',lambda d:next(n for n in d['nodes'] if n['disposition']=='unresolved').update(disposition='implemented'))]:
        d=deepcopy(delta);mutate(d)
        try:check(base,graph,d,matches,families,calls,support,deferred['placeholders'])
        except ValueError as e:require(str(e)=='DISPATCH_BODY_DELTA','DISPATCH_CONTROL_REASON')
        else:raise ValueError('DISPATCH_CONTROL_ESCAPED '+name)
        tests.append(dict(name=name,status='REJECTED'))
    from support import load_module
    errors=load_module('dispatch_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),
            'DISPATCH_GRAPH_STRUCTURE')
    for name,value in [('body-correspondences.json.gz',dict(matches=matches,support_matches=support)),
                       ('ir.json.gz',dict(functions=families,calls=calls)),('delta.json.gz',delta),
                       ('census.json.gz',graph),('controls.json',tests)]:save(a.output/name,value)
    summary=dict(status='PASS',bodies=len(matches),remaining_dispatch_bodies=0,controls=len(tests),
        computed_call_bounds_transferred=False,census_status='BLOCKED')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','previous','bodies','requests','base','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
