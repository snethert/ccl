"""Give every observed method an explicit body witness or a remaining gap."""
from collections import Counter
from pathlib import Path
from payloads import capture,rows,read,save,require
from accessors import classify


def all_methods(events):
    found={};first={}
    for event in events:
        states=event['entries'] if event['kind']=='registry-checkpoint' else (
            [event['gf']] if event['kind'] in ('mutation-enter','mutation-leave') else [])
        for state in states:
            if state is None or state['status']=='UNINITIALIZED':continue
            for m in state['methods']:
                # Removal mutates the owner in the detached record, not an
                # entry held by a GF. Registry entries keep their actual owner.
                require(m['id'] not in found or found[m['id']]==m,'METHOD_REGISTRY_IDENTITY')
                found[m['id']]=m;first.setdefault(m['id'],event['build_event'])
    return found,first


def assemble(functions,emissions,before,loader,registries,templates,body_matches):
    population,first=all_methods(registries);bodies={m['bootstrap_code']:m for m in body_matches}
    result=[]
    for ident,m in sorted(population.items()):
        f=functions[m['function']];proto=f['prototype'];at=first[ident]
        compiled=[e for e in emissions.get(proto,[]) if e['afunc'] in before and e['event']<at]
        loaded=[e for e in loader.get(proto,[]) if e['afunc'] in before and e['event']<at]
        witness=None
        if compiled:witness=dict(kind='COMPILER_MATERIALIZATION',records=compiled)
        elif loaded:witness=dict(kind='FASL_VERSION',records=loaded)
        else:
            accessor=classify(f,ident,templates)
            if accessor:witness=dict(kind='ACCESSOR_TEMPLATE',record=accessor)
            elif proto in bodies:witness=dict(kind='EXECUTION_BODY_CORRESPONDENCE',prototype=proto)
        result.append(dict(method=m,first_observation=at,prototype=proto,
            witness=witness,body_status='QUALIFIED_DEPENDENCIES' if witness else 'UNRESOLVED',
            runtime_dispatch_bound=False))
    return result


def run(output):
    f,em,_,_,_=capture(output/'registries.jsonl.gz')
    before={int(k):v for k,v in read(output/'compiler-index-v2.json.gz')['before'].items()}
    loader={int(k):v for k,v in read(output/'loader-body-joins.json.gz')['joins'].items()}
    templates=read(output/'accessor-template-joins.json.gz')['templates']
    nested=read(output/'nested-body-correspondences.json.gz')
    result=assemble(f,em,before,loader,rows(output/'registries.jsonl.gz'),templates,
                    nested['matches']+nested['support_matches'])
    expected={m['id']:m for g in read(output/'registry-loader-replay.json.gz')['registries'] for m in g['methods']}
    require({r['method']['id']:r['method'] for r in result}==expected,'METHOD_REGISTRY_POPULATION')
    summary=dict(status='PASS',methods=len(result),body_witnesses=dict(Counter(
        r['witness']['kind'] if r['witness'] else 'UNRESOLVED' for r in result)),runtime_exhaustive=False)
    save(output/'method-body-joins.json.gz',result);save(output/'method-body-summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);run(p.parse_args().output)
