"""Replay real method-store operations across the correlated native rebuild.

An observed registry union is not a bound on later ADD-METHOD calls. The replay
names any construction or direct-store gap rather than completing that bound.
"""
from collections import Counter,defaultdict
from pathlib import Path
from payloads import rows,capture,require,save,before_functions


def methods(state):
    if state is None or state['status']=='UNINITIALIZED':return None
    return state['methods']


def state_check(state,functions):
    if state is None:return
    ident=state['gf'];require(ident in functions,'GF_FUNCTION_REFERENCE')
    bits=functions[ident]['bits']
    require(bits & (1<<27) and not bits & (1<<28),'GF_FUNCTION_TYPE')
    if state['status']=='UNINITIALIZED':
        require(bool(state['unbound_slots']),'UNINITIALIZED_FIELDS');return
    require(state['status']=='INITIALIZED' and state['native_standard_gf'] is True
            and state['slots_owner_matches'] is True,'REGISTRY_STATE')
    require(state['dcode'] in functions,'DCODE_FUNCTION_REFERENCE')
    entries=state['methods']
    require(len({m['id'] for m in entries})==len(entries),'DUPLICATE_REGISTRY_METHOD')
    for m in entries:
        require(m['owner']==ident,'REGISTRY_METHOD_OWNER')
        require(m['function'] in functions and functions[m['function']]['bits'] & (1<<28),'METHOD_FUNCTION_REFERENCE')


def replay(events,functions,emissions,before,loader_bodies=None):
    initial=None;final=None;active=[];entered={};last={};seen=defaultdict(list)
    operations=[];gaps=[];counts=Counter();allstates=[]
    for e in events:
        kind=e['kind']
        if kind=='registry-checkpoint':
            for s in e['entries']:state_check(s,functions)
            d={s['gf']:s for s in e['entries']}
            require(len(d)==len(e['entries']),'REGISTRY_POPULATION_DUPLICATE')
            if e['stage']=='before':
                require(initial is None,'REGISTRY_INITIAL_DUPLICATE');initial=d;last.update(d)
            else:
                require(e['stage']=='after' and final is None,'REGISTRY_FINAL_DUPLICATE');final=d
            allstates.extend(e['entries'])
        elif kind=='mutation-enter':
            require(initial is not None and final is None,'MUTATION_PHASE')
            s=e['gf'];state_check(s,functions);allstates.append(s)
            operation=e['operation']['symbol'];counts[operation]+=1
            require(operation in ('%ADD-STANDARD-METHOD-TO-STANDARD-GF',
                '%REMOVE-STANDARD-METHOD-FROM-CONTAINING-GF','%SET-GF-DCODE'),'REGISTRY_OPERATION')
            if s is not None:
                gf=s['gf']
                if not any(entered[x]['gf'] and entered[x]['gf']['gf']==gf for x in active):
                    prior=last.get(gf)
                    if methods(prior) is not None and methods(prior)!=methods(s):
                        gaps.append(dict(gf=gf,event=e['sequence'],kind='UNOBSERVED_METHOD_STATE_CHANGE',
                                         before=prior,after=s))
                    if prior is None:
                        gaps.append(dict(gf=gf,event=e['sequence'],kind='REGISTRY_CONSTRUCTION',state=s))
                seen[gf].append(e['sequence'])
            entered[e['sequence']]=e;active.append(e['sequence'])
        elif kind=='mutation-leave':
            require(active and active.pop()==e['entry'] and e['completed'] is True,'REGISTRY_OPERATION_PAIR')
            enter=entered[e['entry']];a=enter['gf'];b=e['gf'];state_check(b,functions);allstates.append(b)
            op=enter['operation']['symbol'];m=enter['method'];n=e['method']
            require((a is None)==(b is None),'REGISTRY_GF_CHANGE')
            if a is None:
                require(op=='%REMOVE-STANDARD-METHOD-FROM-CONTAINING-GF' and m==n and m['owner'] is None,
                        'UNOWNED_REMOVE');continue
            gf=a['gf'];require(b['gf']==gf,'REGISTRY_GF_CHANGE')
            if op=='%SET-GF-DCODE':
                require(m is None and n is None and methods(a)==methods(b),
                        'REGISTRY_DCODE_TRANSITION')
                if b['status']=='INITIALIZED':
                    require(b['dcode']==enter['dcode'],'REGISTRY_DCODE_TARGET')
                else:
                    gaps.append(dict(gf=gf,event=e['sequence'],kind='UNINITIALIZED_DCODE_STATE',
                                     requested=enter['dcode'],state=b))
            else:
                require(methods(a) is not None and methods(b) is not None,'REGISTRY_METHOD_INITIALIZATION')
                require(m['id']==n['id'] and {k:v for k,v in m.items() if k!='owner'}==
                        {k:v for k,v in n.items() if k!='owner'},'REGISTRY_METHOD_MUTATION')
                if op=='%ADD-STANDARD-METHOD-TO-STANDARD-GF':
                    replaced=[x for x in a['methods'] if x['qualifiers']==m['qualifiers'] and x['specializers']==m['specializers']]
                    require(len(replaced)<=1,'REGISTRY_AMBIGUOUS_REPLACEMENT')
                    expected=[n]+[x for x in a['methods'] if x not in replaced]
                    require(n['owner']==gf and b['methods']==expected,'REGISTRY_ADD_TRANSITION')
                else:
                    require(m['owner']==gf and n['owner'] is None and m in a['methods']
                            and b['methods']==[x for x in a['methods'] if x['id']!=m['id']],
                            'REGISTRY_REMOVE_TRANSITION')
                proto=functions[n['function']]['prototype']
                bodies=[x for x in emissions.get(proto,[]) if x['afunc'] in before and x['event']<enter['build_event']]
                bodies+=[x for x in (loader_bodies or {}).get(proto,[]) if x['afunc'] in before and x['event']<enter['build_event']]
                operations.append(dict(gf=gf,operation=op,entry=enter['sequence'],completed=e['sequence'],
                    method=n['id'],function=n['function'],prototype=proto,compiler_bodies=bodies))
            last[gf]=b
    require(initial is not None and final is not None and not active,'REGISTRY_REPLAY_COMPLETION')
    for gf,s in final.items():
        prior=last.get(gf)
        if methods(prior)!=methods(s):gaps.append(dict(gf=gf,kind='UNOBSERVED_FINAL_METHOD_STATE',before=prior,after=s))
    union=defaultdict(lambda:dict(methods={},dcodes=set(),states=0))
    for s in allstates:
        if methods(s) is None:continue
        u=union[s['gf']];u['states']+=1;u['dcodes'].add(s['dcode'])
        for m in s['methods']:
            old=u['methods'].get(m['id'])
            require(old is None or old==m,'OBSERVED_METHOD_IDENTITY_CHANGED')
            u['methods'][m['id']]=m
    registry=[dict(gf=gf,states=u['states'],dcodes=sorted(u['dcodes']),
                   methods=[u['methods'][m] for m in sorted(u['methods'])],
                   runtime_bound='UNRESOLVED_FUTURE_MUTATIONS') for gf,u in sorted(union.items())]
    summary=dict(initial_gfs=len(initial),final_gfs=len(final),observed_gfs=len(registry),
        operations=dict(counts),method_operations=len(operations),
        method_body_joins=sum(bool(o['compiler_bodies']) for o in operations),
        method_construction_gaps=sum(not o['compiler_bodies'] for o in operations),
        state_gaps=dict(Counter(g['kind'] for g in gaps)),runtime_exhaustive=False)
    return dict(registries=registry,operations=operations,state_gaps=gaps),summary


def run(output):
    f,em,_,_,_=capture(output/'registries.jsonl.gz')
    facts,summary=replay(rows(output/'registries.jsonl.gz'),f,em,before_functions(output/'build.jsonl.gz',em))
    save(output/'registry-replay.json.gz',facts);save(output/'registry-summary.json',summary);print(summary)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);run(p.parse_args().output)
