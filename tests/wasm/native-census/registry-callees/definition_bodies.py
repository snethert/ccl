"""Join source-less named bodies to exact-cell compiler definitions.

This preserves native code/constant checks and a closed nested-code relation.
It does not claim that a compiled definition was ever installed or that its
initializers, metadata and captured environments equal those of the old image.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import hashlib
from payloads import read,save,require,capture,dependency_body_key,correspondences
from bodies import selected_rows,extract,make,apply,with_initializers,needed_matches
from nested_bodies import materialized_candidates,closure,pairs,qualify
from deferred import index as deferred_index

HERE=Path(__file__).resolve().parent


def anchors(bindings,requested,functions,emissions,before,events):
    cells=defaultdict(list)
    for b in bindings:
        if b['kind']=='resident-binding' and b['stage']=='before' and b['value']['role']=='function' and b['symbol'].get('kind')=='symbol':
            code=b['value']['code']
            if code in requested and functions[code]['source'] is None:cells[b['symbol']['id']].append(b)
    result={}
    for event in events:
        require(event['kind']=='before-pass2','DEFINITION_BODY_PHASE')
        p=event['payload'];ns={n['id']:n for n in p['ir']['objects']};root=ns[p['ir']['root']['ref']]
        require(root['kind']=='afunc' and root['parent'] is None and root['id']==p['function']['function_id'],
                'DEFINITION_BODY_ROOT')
        symbol=ns.get(root['name'].get('ref'))
        if not symbol or symbol['kind']!='symbol':continue
        for initial in cells[symbol['id']]:
            require(initial['symbol']==symbol and initial['sequence']<event['sequence'],'DEFINITION_BODY_CELL')
            for fn,e in emissions.get(root['id'],[]):
                require(before[root['id']]['event']==event['sequence']<e['event'],'DEFINITION_BODY_ORDER')
                result[initial['value']['code'],fn,root['id']]=dict(initial=initial,
                    definition=dict(symbol=symbol,afunc=root['id'],event=event['sequence'],source=event['source'],
                                    source_position=event['source_position']),materialization=dict(function=fn,**e))
    return result


def anchor_controls(bindings,requested,functions,emissions,before,events,witnesses):
    result=[];key=next(iter(witnesses));w=witnesses[key]
    event=next(e for e in events if e['sequence']==w['definition']['event'])
    def change_symbol(**fields):
        row=deepcopy(event);ns=row['payload']['ir']['objects']
        next(n for n in ns if n['id']==w['definition']['symbol']['id']).update(fields)
        return row
    # Several U1 functions emit identical constant-return instructions. Their
    # actual symbol cells must still prevent a name/byte-only source join.
    changed=deepcopy(event);root=next(n for n in changed['payload']['ir']['objects'] if n['id']==key[2])
    root['name']={'integer':19}
    require(key not in anchors(bindings,requested,functions,emissions,before,[changed]),'DEFINITION_UNNAMED_PROMOTED')
    result.append(dict(name='unnamed-definition-is-not-cell-definition',status='REJECTED'))
    changed=change_symbol(id=-1)
    root=next(n for n in changed['payload']['ir']['objects'] if n['id']==key[2]);root['name']={'ref':-1}
    require(key not in anchors(bindings,requested,functions,emissions,before,[changed]),'DEFINITION_HOMONYM_PROMOTED')
    result.append(dict(name='same-spelling-other-symbol',status='REJECTED'))
    for name,mutant,reason in [
        ('alter-exact-symbol-description',change_symbol(name='SUBSTITUTED'),'DEFINITION_BODY_CELL'),
        ('claim-frontend-is-pass2',dict(event,kind='frontend'),'DEFINITION_BODY_PHASE'),
        ('reverse-compilation-order',dict(event,sequence=w['materialization']['event']+1),'DEFINITION_BODY_ORDER')]:
        try:anchors(bindings,requested,functions,emissions,before,[mutant])
        except ValueError as e:require(str(e)==reason,'DEFINITION_CONTROL_REASON '+name)
        else:raise ValueError('DEFINITION_CONTROL_ESCAPED '+name)
        result.append(dict(name=name,status='REJECTED'))
    return result


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    fs,em,_,wrappers,_=capture(a.capture/'registries.jsonl.gz')
    idx=read(a.previous/'compiler-index.json.gz');before={int(k):v for k,v in idx['before'].items()}
    late={int(k):v for k,v in idx['late_notes'].items()}
    loader={int(k):v for k,v in read(a.previous/'loader-body-joins.json.gz')['joins'].items()}
    combined=materialized_candidates(fs,em,loader)
    missing=set(read(a.replaced/'remaining.json'))
    old=read(a.bodies/'body-correspondences.json.gz')
    # Decode only before-pass2 families whose materialized body could match.
    coarse=lambda f:dependency_body_key(f,True)[:3]+(len(dependency_body_key(f,True)[3]),)
    keys={coarse(fs[i]) for i in missing if fs[i]['source'] is None}
    selected={};by_afunc=defaultdict(list)
    for i,records in em.items():
        if fs[i]['prototype']!=i or coarse(fs[i]) not in keys:continue
        for e in records:
            b=before.get(e['afunc'])
            if b and b['parent'] is None:
                selected[b['event']]=True;by_afunc[e['afunc']].append((i,e))
    events=list(selected_rows(a.capture/'build.jsonl.gz',set(selected)))
    require({e['sequence'] for e in events}==set(selected),'DEFINITION_EVENT_COVERAGE')
    bindings=read(a.bindings)
    witnessed=anchors(bindings,missing,fs,by_afunc,before,events)
    require(witnessed,'DEFINITION_BODY_NO_WITNESSES')
    tests=anchor_controls(bindings,missing,fs,by_afunc,before,events,witnessed)
    requested=closure(fs,missing|{m['bootstrap_code'] for m in old['support_matches']})
    asks=dict(bodies=[dict(code=i,payload_sha256=hashlib.sha256(bytes.fromhex(fs[i]['payload_hex'])).hexdigest()) for i in sorted(requested)])
    deferred=read(a.bodies/'deferred-initializers.json.gz')
    candidates,_=correspondences(fs,combined,wrappers,asks,before,late,read(a.previous/'source-coordinate-map.json'),
        data_dependencies=True,candidate_function_literals=True,deferred=deferred_index(deferred),definition_witnesses=witnessed)
    relation,_=pairs(fs,candidates);qualified=qualify(fs,candidates,relation)
    new=[m for m in qualified if m['bootstrap_code'] in missing]
    support={m['bootstrap_code']:m for m in old['matches']+old['support_matches']+qualified}
    roots={m['bootstrap_code'] for m in new};extra=[m for i,m in support.items() if i not in roots]
    require(roots,'DEFINITION_BODY_NO_PROGRESS')
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    families,calls=extract(a.capture/'build.jsonl.gz',with_initializers(needed_matches(new,extra),deferred['placeholders']),ops)
    base=read(a.base);delta=make(base,new,families,calls,extra,deferred['placeholders'],namespace='defined-bodies:');graph=apply(base,delta)
    save(a.output/'definition-witnesses.json.gz',list(witnessed.values()))
    save(a.output/'body-correspondences.json.gz',dict(matches=new,support_matches=extra))
    for name,value in [('controls.json',tests),('delta.json.gz',delta),('census.json.gz',graph),
                       ('ir.json.gz',dict(functions=families,calls=calls)),('remaining.json',sorted(missing-roots))]:save(a.output/name,value)
    from support import load_module
    errors=load_module('definition_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'DEFINITION_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',new_bodies=len(new),remaining_readonly_bodies=len(missing-roots),
                 definition_witnesses=len(witnessed),controls=len(tests),installation_claimed=False,caller_bounds_transferred=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','previous','bodies','replaced','bindings','base','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
