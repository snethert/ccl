"""Qualify nested native code pairs by a closed literal-reference relation.

Matching code and source alone does not qualify a function constant. Each
different function literal must itself have a surviving body pair. The greatest
fixed point permits recursive literal graphs without assuming any caller state.
It asserts a body relation, never function-object or environment identity.
"""
from collections import defaultdict,deque
from copy import deepcopy
from pathlib import Path
import hashlib
from payloads import (capture,read,save,require,literal_regions,correspondences)


def closure(functions,roots):
    seen=set();pending=deque(roots)
    while pending:
        ident=pending.popleft()
        if ident in seen:continue
        require(ident in functions,'NESTED_FUNCTION_REFERENCE');seen.add(ident)
        pending.extend(v['function'] for v in literal_regions(functions[ident])[0]
                       if isinstance(v,dict) and 'function' in v)
    return seen


def pairs(functions,candidates):
    relation={(m['bootstrap_code'],f) for m in candidates for f in m['compiled_functions']}
    requirements={};reverse=defaultdict(set)
    for pair in relation:
        a,b=pair;left=literal_regions(functions[a])[0];right=literal_regions(functions[b])[0]
        require(len(left)==len(right),'NESTED_LITERAL_LAYOUT')
        deps=set()
        for x,y in zip(left,right):
            if isinstance(x,dict) and 'function' in x:
                require(isinstance(y,dict) and 'function' in y,'NESTED_CALLABLE_KIND')
                if x['function']!=y['function']:deps.add((x['function'],y['function']))
        requirements[pair]=deps
        for dependency in deps:reverse[dependency].add(pair)
    refused={p for p in relation if not requirements[p]<=relation};queue=deque(refused)
    while queue:
        for parent in reverse[queue.popleft()]-refused:
            refused.add(parent);queue.append(parent)
    result=relation-refused
    require(all(requirements[p]<=result for p in result),'NESTED_RELATION_NOT_CLOSED')
    return result,requirements


def qualify(functions,candidates,relation):
    result=[]
    for original in candidates:
        a=original['bootstrap_code'];bs={b for old,b in relation if old==a}
        if not bs:continue
        m=deepcopy(original);m.pop('candidate_only');m.pop('function_dependencies')
        m['compiled_functions']=sorted(bs)
        m['compiler_records']=[e for e in m['compiler_records'] if e['function'] in bs]
        for item in m.get('data_dependencies',[]):
            item['compiled_literals']={k:v for k,v in item['compiled_literals'].items() if int(k) in bs}
            if 'deferred_initializers' in item:
                item['deferred_initializers']={k:v for k,v in item['deferred_initializers'].items() if int(k) in bs}
        if 'late_source_notes' in m:m['late_source_notes']={k:v for k,v in m['late_source_notes'].items() if int(k) in bs}
        dependencies=[]
        for index,x in enumerate(literal_regions(functions[a])[0]):
            if not isinstance(x,dict) or 'function' not in x:continue
            for b in sorted(bs):
                y=literal_regions(functions[b])[0][index]
                if x['function']!=y['function']:
                    require((x['function'],y['function']) in relation,'NESTED_PAIR_NOT_QUALIFIED')
                dependencies.append(dict(index=index,compiled_owner=b,bootstrap_function=x['function'],
                    compiled_function=y['function'],relation=('QUALIFIED_EXECUTION_BODY'
                        if x['function']!=y['function'] else 'EXACT_LITERAL_IDENTITY'),
                    function_identity=(x['function']==y['function']),environment_identity=False))
        if dependencies:m['function_literal_correspondences']=dependencies
        m['scope']='Native execution-body dependencies with a closed nested-code relation; metadata, noncallable data and caller/enclosing environments are not identified. Computed targets remain unresolved.'
        result.append(m)
    return result


def materialized_candidates(functions,emissions,loader):
    combined={k:list(v) for k,v in emissions.items()}
    for ident,records in loader.items():
        if ident in functions:combined.setdefault(ident,[]).extend(records)
    return combined


def run(output,evidence):
    f,em,_,wr,_=capture(output/'registries.jsonl.gz')
    idx=read(output/'compiler-index-v2.json.gz');before={int(k):v for k,v in idx['before'].items()}
    late={int(k):v for k,v in idx['late_notes'].items()}
    loader={int(k):v for k,v in read(output/'loader-body-joins.json.gz')['joins'].items()}
    em=materialized_candidates(f,em,loader)
    old=read(evidence/'2026-09-14-resident-bodies-r1/bodies.json.gz')
    original={b['code']:b for b in old['bodies']}
    all_roots=set(original)|{m['function'] for m in read(output/'all-method-work.json.gz')['remaining']}
    population=closure(f,all_roots)
    requested={'bodies':[original[k] if k in original else dict(code=k,
        payload_sha256=hashlib.sha256(bytes.fromhex(f[k]['payload_hex'])).hexdigest()) for k in sorted(population)]}
    candidates,missing=correspondences(f,em,wr,requested,before,late,read(output/'source-coordinate-map.json'),
        data_dependencies=True,candidate_function_literals=True)
    relation,requirements=pairs(f,candidates);matched=qualify(f,candidates,relation)
    roots=[m for m in matched if m['bootstrap_code'] in original]
    save(output/'nested-body-correspondences.json.gz',dict(matches=roots,
        support_matches=[m for m in matched if m['bootstrap_code'] not in original],
        remaining_codes=sorted(set(original)-{m['bootstrap_code'] for m in roots}),
        relation=[dict(bootstrap=a,compiled=b,requires=[list(p) for p in sorted(requirements[(a,b)])]) for a,b in sorted(relation)]))
    summary=dict(status='PASS',original_body_matches=len(roots),remaining_original_readonly=4373-len(roots),
        candidate_bodies=len(candidates),candidate_pairs=sum(len(m['compiled_functions']) for m in candidates),
        qualified_pairs=len(relation),qualified_bodies=len(matched),reference_population=len(population),
        function_identity_claims=0,caller_environment_bounds=0)
    save(output/'nested-body-summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parents[5]/'ccl-evidence')
    a=p.parse_args();run(a.output,a.evidence)
