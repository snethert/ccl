"""Extend the working census with deferred-constant initializer dependencies."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import sys
import traceback
from payloads import capture,read,save,require,correspondences
from deferred import collect,index,check_links
from nested_bodies import closure,materialized_candidates,pairs,qualify
from methods import assemble as method_bodies
from payloads import rows
from bodies import extract,make,apply,needed_matches,with_initializers

HERE=Path(__file__).resolve().parent


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    require(read(a.capture/'run.json')['status']=='PASS' and read(a.previous/'summary.json')['status']=='PASS',
            'DEFERRED_PREVIOUS_RUN')
    print('Reading the native function capture and completed compiler/loader joins.',flush=True)
    functions,emissions,_,wrappers,_=capture(a.capture/'registries.jsonl.gz')
    previous=read(a.previous/'compiler-index.json.gz')
    before={int(k):v for k,v in previous['before'].items()};late={int(k):v for k,v in previous['late_notes'].items()}
    loader={int(k):v for k,v in read(a.previous/'loader-body-joins.json.gz')['joins'].items()}
    coordinates=read(a.previous/'source-coordinate-map.json')
    deferred=collect(a.capture/'build.jsonl.gz',functions,emissions,before,a.source,coordinates,loader)
    save(a.output/'deferred-initializers.json.gz',deferred)
    print('Joined',len(deferred['placeholders']),'deferred literal observations.',flush=True)
    old={r['code']:r for r in read(a.evidence/'2026-09-14-resident-bodies-r1/bodies.json.gz')['bodies']}
    old_methods=read(a.previous/'method-body-joins.json.gz')
    requested_codes=closure(functions,set(old)|{r['prototype'] for r in old_methods})
    requested={'bodies':[old[k] if k in old else dict(code=k,
        payload_sha256=hashlib.sha256(bytes.fromhex(functions[k]['payload_hex'])).hexdigest()) for k in sorted(requested_codes)]}
    combined=materialized_candidates(functions,emissions,loader)
    candidates,_=correspondences(functions,combined,wrappers,requested,before,late,coordinates,
            data_dependencies=True,candidate_function_literals=True,deferred=index(deferred))
    relation,requirements=pairs(functions,candidates);all_matches=qualify(functions,candidates,relation)
    matches=[m for m in all_matches if m['bootstrap_code'] in old]
    support=[m for m in all_matches if m['bootstrap_code'] not in old]
    old_matched={r['bootstrap_code'] for r in read(a.previous/'body-correspondences.json.gz')['matches']}
    require(old_matched<={m['bootstrap_code'] for m in matches},'DEFERRED_LOST_PREVIOUS_BODY')
    methods=method_bodies(functions,emissions,before,loader,rows(a.capture/'registries.jsonl.gz'),
                         read(a.previous/'accessor-templates.json'),all_matches)
    require({r['method']['id']:r['method'] for r in methods}=={r['method']['id']:r['method'] for r in old_methods},
            'DEFERRED_METHOD_POPULATION')
    save(a.output/'body-correspondences.json.gz',dict(matches=matches,support_matches=support,
         remaining_codes=sorted(set(old)-{m['bootstrap_code'] for m in matches})))
    save(a.output/'method-body-joins.json.gz',methods)
    print('Bodies joined:',len(matches),'; remaining method bodies:',sum(r['witness'] is None for r in methods),flush=True)
    del functions,emissions,combined,candidates,before,late
    sample=next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    operators={int(k):v for k,v in sample['operators'].items()}
    selection=with_initializers(needed_matches(matches,support),deferred['placeholders'])
    families,calls=extract(a.capture/'build.jsonl.gz',selection,operators)
    save(a.output/'ir.json.gz',dict(functions=families,calls=calls))
    base=read(a.base);delta=make(base,matches,families,calls,support,deferred['placeholders']);graph=apply(base,delta)
    check_links(graph,deferred['placeholders'])
    save(a.output/'delta.json.gz',delta);save(a.output/'census.json.gz',graph)
    from support import load_module
    errors=load_module('deferred_census_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
    require(all(e.startswith(prefixes) for e in errors),'DEFERRED_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',body_gaps_joined=len(matches),
        new_body_joins=len(matches)-len(old_matched),remaining_readonly_bodies=len(old)-len(matches),
        method_population=len(methods),method_body_witnesses=dict(Counter(
          r['witness']['kind'] if r['witness'] else 'UNRESOLVED' for r in methods)),
        deferred_observations=len(deferred['placeholders']),unjoined_initializers=len(deferred['unjoined']),
        initializer_functions=len({r['function'] for r in deferred['placeholders']}),
        reachable_initializer_nodes=sum(n['id'].startswith('correlated-build:deferred:') for n in delta['nodes']),
        initializer_results_qualified=False,initializer_effects_qualified=False,borrowed_caller_bounds=0,
        graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
        unresolved_edges=sum(e.startswith(prefixes[0]) for e in errors),
        unimplemented_nodes=sum(e.startswith(prefixes[1]) for e in errors))
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','previous','source','base','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
