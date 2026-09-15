"""Damage the small real native mutation run; never rebuild to test the reader."""
from copy import deepcopy
from pathlib import Path
from payloads import capture,rows,before_functions,require
from registry import replay


def run(probe):
    functions,emissions,_,_,_=capture(probe/'registries.jsonl')
    before=before_functions(probe/'events.jsonl',emissions)
    events=list(rows(probe/'registries.jsonl'))
    facts,summary=replay(events,functions,emissions,before)
    require(summary['method_operations']==5 and summary['method_body_joins']==2,'NATIVE_PROBE_POPULATION')
    controls=[]
    def reject(name,mutate,reason):
        es=deepcopy(events);mutate(es)
        try:replay(es,functions,emissions,before)
        except ValueError as e:
            require(str(e)==reason,'REGISTRY_CONTROL_REASON '+name+' '+str(e));controls.append(name);return
        raise ValueError('REGISTRY_CONTROL_ESCAPED '+name)
    def added(es):
        entries={e['sequence']:e for e in es if e['kind']=='mutation-enter'}
        return next(e for e in es if e['kind']=='mutation-leave'
                    and entries[e['entry']]['operation']['symbol']=='%ADD-STANDARD-METHOD-TO-STANDARD-GF')
    reject('missing-installed-method',lambda es:added(es)['gf']['methods'].pop(0),'REGISTRY_ADD_TRANSITION')
    reject('wrong-method-owner',lambda es:added(es)['gf']['methods'][0].update(owner=-1),'REGISTRY_METHOD_OWNER')
    reject('unknown-method-body',lambda es:added(es)['gf']['methods'][0].update(function=-1),'METHOD_FUNCTION_REFERENCE')
    reject('unfinished-operation',lambda es:added(es).update(completed=False),'REGISTRY_OPERATION_PAIR')
    def corrupt_dcode(es):
        entries={e['sequence']:e for e in es if e['kind']=='mutation-enter'}
        e=next(e for e in es if e['kind']=='mutation-leave' and e['gf']['status']=='INITIALIZED'
               and entries[e['entry']]['operation']['symbol']=='%SET-GF-DCODE')
        entries[e['entry']]['dcode']=-1
    reject('wrong-installed-dcode',corrupt_dcode,'REGISTRY_DCODE_TARGET')
    # Omit the final removal pair. A missing store is diagnosed at the next
    # actual state observation (a later dcode call or the final checkpoint).
    last_remove=next(e for e in reversed(events) if e['kind']=='mutation-enter'
                     and e['operation']['symbol']=='%REMOVE-STANDARD-METHOD-FROM-CONTAINING-GF')
    damaged=[e for e in events if e['sequence']!=last_remove['sequence'] and e.get('entry')!=last_remove['sequence']]
    _,changed=replay(damaged,functions,emissions,before)
    def unseen(s):return sum(v for k,v in s['state_gaps'].items() if k.startswith('UNOBSERVED_'))
    require(unseen(changed)>unseen(summary),'MISSING_STORE_NOT_DIAGNOSED')
    controls.append('omitted-final-store-detected')
    changed=deepcopy(emissions);key=next(iter(changed));changed[key]=changed[key][1:]
    try:before_functions(probe/'events.jsonl',changed)
    except ValueError as e:require(str(e)=='MAIN_SIDE_MATERIALIZATION_JOIN','MISSING_MATERIALIZATION_REASON')
    else:raise ValueError('MISSING_MATERIALIZATION_ESCAPED')
    controls.append('omitted-side-materialization')
    return dict(status='PASS',controls=controls,native_summary=summary)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('probe',type=Path);print(run(p.parse_args().probe))
